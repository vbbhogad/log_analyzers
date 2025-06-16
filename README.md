# log_analyzers

A modular toolkit for analyzing and visualizing various log files using Python and Streamlit.

## Overview

**log_analyzers** provides a user-friendly interface for parsing, analyzing, and visualizing different types of log files. It is designed for engineers, analysts, and developers who need to quickly extract insights from raw logs.

## Features

- 📊 Interactive dashboards for log analysis
- 🗂️ Modular architecture: add new log analyzers easily
- 🔍 Filtering, searching, and aggregation tools
- 📈 Visualizations powered by Altair
- 📝 Example log files for testing

## Directory Structure

```
log_analyzers/
├── streamlit_app.py        # Main Streamlit app entry point
├── pages/                  # Individual analysis modules for each log type
├── logs/                   # Example log files for testing
├── README.md               # Project documentation
└── requirements.txt        # (Optional) Python dependencies
```

## Getting Started

### Prerequisites

- Python 3.8+
- [Streamlit](https://streamlit.io/)
- [Pandas](https://pandas.pydata.org/)
- [NumPy](https://numpy.org/)
- [Altair](https://altair-viz.github.io/)

### Installation

Install dependencies:

```sh
pip install streamlit pandas numpy altair
```

### Usage

1. Place your log files in the `logs/` directory or specify their path in the app.
2. Launch the Streamlit app:

    ```sh
    streamlit run streamlit_app.py
    ```

3. Use the sidebar to select the log type and analysis module.

4. Explore, filter, and visualize your log data interactively.

## Adding a New Log Analyzer

1. Create a new Python file in the `pages/` directory (e.g., `my_log_analyzer.py`).
2. Implement your analysis logic and UI using Streamlit.
3. The new module will appear as a page in the Streamlit sidebar.

## Example Log Files

Sample logs are provided in the `logs/` directory for demonstration and testing.

## Contributing

Contributions are welcome! Please open issues or submit pull requests for new features, bug fixes, or improvements.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
