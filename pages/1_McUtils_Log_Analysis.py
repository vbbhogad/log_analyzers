import streamlit as st
import pandas as pd
import numpy as np
import io
import re

st.title("McUtils Log Memory Bandwidth Analysis")

uploaded_file = st.file_uploader("Upload McUtils Log File containign Memory bandwidth data", type=["log", "txt"])

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

        # Use session_state to persist filtered_df and stats
        if analyze or ("filtered_df" in st.session_state and "stats" in st.session_state):
            if analyze:
                # Filter data based on selections
                filtered_df = df[
                    df['socket'].isin(selected_sockets) &
                    df['mc'].isin(selected_mcs) &
                    df['ch'].isin(selected_chs)
                ]
                st.session_state["filtered_df"] = filtered_df
            else:
                filtered_df = st.session_state["filtered_df"]

            if filtered_df.empty:
                st.warning("No data available for the selected filters.")
            else:
                st.subheader("Parsed Raw Data for Memory Bandwidth (GB/s)")
                st.dataframe(filtered_df)

                # Statistics
                if analyze or "stats" not in st.session_state:
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
                    st.session_state["stats"] = stats
                else:
                    stats = st.session_state["stats"]

                st.subheader("Memory Bandwidth Statistics (GB/s)")
                st.dataframe(stats)

                # Bar Chart for Statistics (Moved and Modified)
                st.subheader("Bandwidth Statistics Bar Chart")
                import altair as alt # Ensure altair is imported if not already in this scope

                # Prepare data for bar chart
                stats_chart_df = stats.copy()
                stats_chart_df['MC_CH'] = stats_chart_df['mc'].astype(str) + '_' + stats_chart_df['ch'].astype(str)

                all_stat_cols = [col for col in stats.columns if col not in ['mc', 'ch', 'sample_count']]
                possible_defaults = ['avg_read', 'avg_write', 'p95_read', 'p95_write']
                default_stat_selection = [s for s in possible_defaults if s in all_stat_cols]
                if not default_stat_selection and all_stat_cols:
                    default_stat_selection = all_stat_cols[:min(2, len(all_stat_cols))]

                selected_stat_types = st.multiselect(
                    "Select Statistics to Plot",
                    options=all_stat_cols,
                    default=default_stat_selection
                )

                unique_mc_ch_stats = sorted(stats_chart_df['MC_CH'].unique())
                selected_mc_ch_instances = st.multiselect(
                    "Select MC_CH Instances for Bar Chart",
                    options=unique_mc_ch_stats,
                    default=unique_mc_ch_stats
                )

                draw_stat_charts = st.button("Draw Stat Charts")
                if draw_stat_charts:
                    if selected_stat_types and selected_mc_ch_instances:
                        stats_melted = stats_chart_df.melt(
                            id_vars=['MC_CH', 'mc', 'ch'],
                            value_vars=selected_stat_types,
                            var_name='statistic_name',
                            value_name='value'
                        )
                        stats_to_plot = stats_melted[stats_melted['MC_CH'].isin(selected_mc_ch_instances)]
                        if not stats_to_plot.empty:
                            bar_chart = alt.Chart(stats_to_plot).mark_bar().encode(
                                x=alt.X('statistic_name:N', title='Statistic Type', axis=alt.Axis(labelAngle=-45), sort=None),
                                y=alt.Y('value:Q', title='Statistic Value (GB/s)'),
                                color=alt.Color('MC_CH:N', title='MC_CH Instance'),
                                xOffset='MC_CH:N',  # Added to unstack/group bars
                                tooltip=['statistic_name', 'MC_CH', alt.Tooltip('value:Q', title='Value (GB/s)', format='.2f')]
                            ).properties(
                                height=400
                            ).interactive()

                            # Add text labels to display values on each bar, aligned with each bar using xOffset
                            text = alt.Chart(stats_to_plot).mark_text(
                                align='center',
                                baseline='bottom',
                                dy=-4,  # move text slightly above the bar
                                fontSize=12
                            ).encode(
                                x=alt.X('statistic_name:N', sort=None),
                                y=alt.Y('value:Q'),
                                xOffset=alt.X('MC_CH:N'),  # Align text with grouped bars
                                text=alt.Text('value:Q', format='.2f'),
                                color=alt.value('black')
                            )

                            st.altair_chart(bar_chart + text, use_container_width=True)
                        else:
                            st.info("No data to display for the selected statistics and MC_CH instances in the bar chart.")
                    elif not selected_stat_types:
                        st.info("Please select at least one statistic type to display the bar chart.")
                    elif not selected_mc_ch_instances:
                        st.info("Please select at least one MC_CH instance to display the bar chart.")

                # Charts
                st.subheader("Memory Bandwidth Over Sample progression (GB/s)")
                # import altair as alt # This import might be redundant if already imported above for the bar chart

                # Prepare a DataFrame for charting with a combined MC_CH column
                chart_df = filtered_df.copy()
                chart_df['MC_CH'] = chart_df['mc'].astype(str) + '_' + chart_df['ch'].astype(str)
                for metric in ['read', 'write', 'req']:
                    st.markdown(f"**{metric.capitalize()} Bandwidth Over Time**")
                    chart = alt.Chart(chart_df).mark_line().encode(
                        x=alt.X('sample_number:O', title='Sample Number', sort=None),
                        y=alt.Y(f'{metric}:Q', title=f'{metric.capitalize()} Bandwidth (GB/s)'),
                        color=alt.Color('MC_CH:N', title='MC_CH'),
                        tooltip=['sample_number', 'MC_CH', alt.Tooltip(f'{metric}:Q', title=f'{metric.capitalize()} (GB/s)')]
                    ).properties(
                        width=700,
                        height=350
                    ).interactive()
                    st.altair_chart(chart, use_container_width=True)

                # The Bar Chart for Statistics section that was previously here has been moved up.
else:
    st.info("Please upload a McUtils log file to begin analysis.")
