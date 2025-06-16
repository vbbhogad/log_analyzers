import streamlit as st
import pandas as pd
import re

st.title("Ethtools Log Analysis")

uploaded_file = st.file_uploader("Upload Ethtool/ifconfig Log File", type=["txt", "log"])

def parse_ports(log):
    # Parse interface blocks
    port_blocks = re.split(r'\n(?=\w[\w\d\-]+: flags=)', log)
    ports = []
    for block in port_blocks:
        lines = block.strip().splitlines()
        if not lines or ':' not in lines[0]:
            continue
        name = lines[0].split(':')[0]
        ip = mac = mtu = speed = duplex = link = None
        rx_packets = rx_bytes = rx_errors = tx_packets = tx_bytes = tx_errors = None
        for line in lines:
            if 'inet ' in line and not ip:
                m = re.search(r'inet ([\d\.]+)', line)
                if m:
                    ip = m.group(1)
            if 'ether ' in line:
                m = re.search(r'ether ([\da-f:]+)', line)
                if m:
                    mac = m.group(1)
            if 'mtu ' in line:
                m = re.search(r'mtu (\d+)', line)
                if m:
                    mtu = m.group(1)
            if 'RX packets' in line:
                m = re.search(r'RX packets (\d+)\s+bytes (\d+)', line)
                if m:
                    rx_packets, rx_bytes = m.group(1), m.group(2)
            if 'TX packets' in line:
                m = re.search(r'TX packets (\d+)\s+bytes (\d+)', line)
                if m:
                    tx_packets, tx_bytes = m.group(1), m.group(2)
            if 'RX errors' in line:
                m = re.search(r'RX errors (\d+)', line)
                if m:
                    rx_errors = m.group(1)
            if 'TX errors' in line:
                m = re.search(r'TX errors (\d+)', line)
                if m:
                    tx_errors = m.group(1)
            if 'Speed:' in line:
                m = re.search(r'Speed:\s*([\w/]+)', line)
                if m:
                    speed = m.group(1)
            if 'Duplex:' in line:
                m = re.search(r'Duplex:\s*(\w+)', line)
                if m:
                    duplex = m.group(1)
            if 'Link detected:' in line:
                m = re.search(r'Link detected:\s*(\w+)', line)
                if m:
                    link = m.group(1)
        ports.append({
            "Port": name, "IP": ip, "MAC": mac, "MTU": mtu, "Speed": speed, "Duplex": duplex, "Link": link,
            "RX Packets": rx_packets, "RX Bytes": rx_bytes, "RX Errors": rx_errors,
            "TX Packets": tx_packets, "TX Bytes": tx_bytes, "TX Errors": tx_errors
        })
    return pd.DataFrame(ports)

def parse_packet_sizes(log):
    # Find all rx_size_* and tx_size_* lines
    rx_sizes = {}
    tx_sizes = {}
    for line in log.splitlines():
        m = re.match(r'\s*rx_size_(\w+)(?:\.nic)?:\s*(\d+)', line)
        if m:
            rx_sizes[m.group(1)] = int(m.group(2))
        m = re.match(r'\s*tx_size_(\w+)(?:\.nic)?:\s*(\d+)', line)
        if m:
            tx_sizes[m.group(1)] = int(m.group(2))
    rx_df = pd.DataFrame(list(rx_sizes.items()), columns=["Packet Size", "RX Count"])
    tx_df = pd.DataFrame(list(tx_sizes.items()), columns=["Packet Size", "TX Count"])
    return rx_df, tx_df

def parse_link_stats(log):
    # Extract total RX/TX bytes, packets, errors, dropped, multicast, broadcast
    stats = {}
    for line in log.splitlines():
        for key in ["rx_bytes", "tx_bytes", "rx_packets", "tx_packets", "rx_errors", "tx_errors", "rx_dropped", "tx_dropped", "rx_multicast", "tx_multicast", "rx_broadcast", "tx_broadcast"]:
            if line.strip().startswith(key + ":"):
                m = re.match(rf'{key}:\s*(\d+)', line.strip())
                if m:
                    stats[key] = int(m.group(1))
    return stats

if uploaded_file:
    log = uploaded_file.read().decode("utf-8")
    # 1. Summary of all ports
    st.header("Port Summary")
    ports_df = parse_ports(log)
    st.dataframe(ports_df)

    # 2. TX and RX packet sizes and corresponding packet counts
    st.header("Packet Size Distribution")
    rx_df, tx_df = parse_packet_sizes(log)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("RX Packet Sizes")
        st.dataframe(rx_df)
        if not rx_df.empty:
            st.bar_chart(rx_df.set_index("Packet Size")["RX Count"])
    with col2:
        st.subheader("TX Packet Sizes")
        st.dataframe(tx_df)
        if not tx_df.empty:
            st.bar_chart(tx_df.set_index("Packet Size")["TX Count"])

    # 3. Additional metrics and visualizations
    st.header("Overall Link Statistics")
    stats = parse_link_stats(log)
    if stats:
        st.json(stats)
        # Visualize RX/TX bytes and packets
        import altair as alt
        df_stats = pd.DataFrame([
            {"Type": "RX", "Bytes": stats.get("rx_bytes", 0), "Packets": stats.get("rx_packets", 0)},
            {"Type": "TX", "Bytes": stats.get("tx_bytes", 0), "Packets": stats.get("tx_packets", 0)},
        ])
        st.subheader("RX/TX Bytes")
        st.bar_chart(df_stats.set_index("Type")["Bytes"])
        st.subheader("RX/TX Packets")
        st.bar_chart(df_stats.set_index("Type")["Packets"])
else:
    st.info("Please upload an Ethtool/ifconfig log file to begin analysis.")
