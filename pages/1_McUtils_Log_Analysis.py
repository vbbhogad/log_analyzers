import streamlit as st
import pandas as pd
import numpy as np
import io
import re

st.title("McUtils Log Analysis")

uploaded_file = st.file_uploader("Upload McUtils Log File", type=["log", "txt"])

@st.cache_data  # Add caching decorator
def parse_mcutils_log(file_content):
    # This parser is adapted for the gnrMcUtils.log table format with prefix
    table_header_pattern = re.compile(r'\| Socket  \| Mc \| Ch \|    Read     \|    Write    \|   Request   \|')
    table_row_pattern = re.compile(r'\|\s*(socket\d+|Total)\s*\|\s*(\d+)?\s*\|\s*(\d+)?\s*\|\s*([\d.]+) G\s*\|\s*([\d.]+) G\s*\|\s*([\d.]+) G\s*\|')
    timestamp_pattern = re.compile(r'^(\d{2}-\d{2} \d{2}:\d{2}):RESULT')
    data = []
    current_timestamp = None
    in_table = False
    block_number = 0  # This will be used as sample_number
    for idx, line in enumerate(file_content.splitlines()):
        # Remove prefix if present
        if ':| Socket  |' in line or ':|  Total  |' in line or ':| socket' in line:
            # Remove everything before the first '|'
            line = line[line.find('|'):]
        ts_match = timestamp_pattern.match(line)
        if ts_match:
            current_timestamp = ts_match.group(1)
        if table_header_pattern.search(line):
            in_table = True
            block_number += 1  # New table block, increment block/sample number
            continue
        if in_table:
            row_match = table_row_pattern.match(line)
            if row_match and current_timestamp:
                socket, mc, ch, read, write, req = row_match.groups()
                if socket == 'Total':
                    mc = ch = 'Total'
                data.append({
                    'line_number': idx + 1,  # 1-based line number in file_content
                    'sample_block': block_number,  # block number for this table
                    'timestamp': pd.to_datetime(current_timestamp, format='%m-%d %H:%M'),
                    'socket': socket,                        
                    'mc': mc if mc else 'Total',
                    'ch': ch if ch else 'Total',                 
                    'read': float(read),
                    'write': float(write),
                    'req': float(req)
                })
            # End of table
            if line.strip().endswith('='):
                in_table = False
    df = pd.DataFrame(data)
    # Add sample_number (increments for each (socket, mc, ch) at each new table block), and socket_number
    if not df.empty:
        # sample_number: for each (socket, mc, ch), increment for each new sample_block
        df['sample_number'] = (
            df.groupby(['socket', 'mc', 'ch'])['sample_block']
            .rank(method='dense').astype(int)
        )
        # socket_number: extract number from 'socket' column if present, else None
        def extract_socket_number(val):
            if isinstance(val, str) and val.startswith('socket'):
                return val.replace('socket', '')
            return None
        df['socket_number'] = df['socket'].apply(extract_socket_number)
        df = df.drop(columns=['sample_block'])
    return df

if uploaded_file:
    content = uploaded_file.read().decode("utf-8")
    df = parse_mcutils_log(content)
    if df.empty:
        st.warning("No valid log entries found. Please check the log format.")
    else:
        # Find unique sockets, MCs, and channels
        sockets = sorted(df['socket'].unique())
        mcs = sorted(df['mc'].unique())
        chs = sorted(df['ch'].unique())

        st.markdown("#### Select Sockets, Memory Controllers, and Channels to Analyze")
        selected_sockets = st.multiselect("Select Sockets", sockets, default=sockets)
        selected_mcs = st.multiselect("Select Memory Controllers (MCs)", mcs, default=mcs)
        selected_chs = st.multiselect("Select Channels", chs, default=chs)

        analyze = st.button("Analyze Log data")

        if analyze:
            # Filter data based on selections
            filtered_df = df[
                df['socket'].isin(selected_sockets) &
                df['mc'].isin(selected_mcs) &
                df['ch'].isin(selected_chs)
            ]

            if filtered_df.empty:
                st.warning("No data available for the selected filters.")
            else:
                st.subheader("Parsed Raw Data (GB/s)")
                st.dataframe(filtered_df)

                # Statistics
                st.subheader("Bandwidth Statistics (GB/s)")
                stats = filtered_df.groupby(['mc', 'ch']).agg(
                    sample_count=('read', 'count'),
                    min_read=('read', 'min'),
                    max_read=('read', 'max'),
                    avg_read=('read', 'mean'),
                    p95_read=('read', lambda x: np.percentile(x, 95)),
                    min_write=('write', 'min'),
                    max_write=('write', 'max'),
                    avg_write=('write', 'mean'),
                    p95_write=('write', lambda x: np.percentile(x, 95)),
                    min_req=('req', 'min'),
                    max_req=('req', 'max'),
                    avg_req=('req', 'mean'),
                    p95_req=('req', lambda x: np.percentile(x, 95)),
                ).reset_index()
                st.dataframe(stats)

                # Charts
                st.subheader("Bandwidth Over Time (GB/s)")
                import altair as alt

                # Prepare a DataFrame for charting with a combined MC_CH column
                # Use a copy to avoid modifying filtered_df if it's used elsewhere,
                # or add directly if only for charting.
                chart_df = filtered_df.copy()
                chart_df['MC_CH'] = chart_df['mc'].astype(str) + '_' + chart_df['ch'].astype(str)
                
                for metric in ['read', 'write', 'req']:
                    st.markdown(f"**{metric.capitalize()} Bandwidth Over Time**")
                    
                    # Optimized chart generation using long-form data directly
                    chart = alt.Chart(chart_df).mark_line().encode(
                        x=alt.X('sample_number:O', title='Sample Number', sort=None), # Assuming sample_number is already ordered
                        y=alt.Y(f'{metric}:Q', title=f'{metric.capitalize()} Bandwidth (GB/s)'),
                        color=alt.Color('MC_CH:N', title='MC_CH'),
                        tooltip=['sample_number', 'MC_CH', alt.Tooltip(f'{metric}:Q', title=f'{metric.capitalize()} (GB/s)')]
                    ).properties(
                        width=700,
                        height=350
                    ).interactive() # Add interactive() for zoom, pan, and interactive legend
                    st.altair_chart(chart, use_container_width=True)
else:
    st.info("Please upload a McUtils log file to begin analysis.")
