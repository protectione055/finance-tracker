# Finance Tracker

A personal finance tracking and analysis tool that helps you understand your spending patterns and make better financial decisions.

## Features

- 📊 **Multi-source Import**: Support for Alipay, WeChat Pay, and bank CSV exports
- 🏷️ **Smart Categorization**: Automatic and manual transaction categorization
- 📈 **Spending Analysis**: Visual reports and insights into spending patterns
- 🔔 **Budget Alerts**: Notifications when approaching budget limits
- 📝 **Multiple Report Formats**: Markdown, HTML, and PDF reports

## Quick Start

### 1. Configuration

```bash
# Copy the example config
cp config/config.example.yaml config/config.yaml

# Edit with your settings
nano config/config.yaml
```

### 2. Import Your Data

Place your exported transaction files in the configured import directories:
- `./data/imports/alipay/` - Alipay CSV exports
- `./data/imports/wechat/` - WeChat Pay CSV exports
- `./data/imports/banks/` - Bank statement CSVs

### 3. Run Analysis

```bash
python -m finance_tracker analyze
```

## Project Structure

```
finance-tracker/
├── config/
│   ├── settings.yaml          # Full configuration template
│   └── config.example.yaml    # Minimal example config
├── src/
│   ├── __init__.py
│   ├── importer.py          # Data import handlers
│   ├── analyzer.py          # Analysis engine
│   ├── categorizer.py       # Transaction categorization
│   ├── reporter.py          # Report generation
│   └── models.py            # Data models
├── templates/
│   └── report_template.md   # Report templates
├── data/
│   ├── imports/             # Import directories
│   │   ├── alipay/
│   │   ├── wechat/
│   │   └── banks/
│   └── finance.db           # SQLite database (auto-created)
├── logs/
│   └── finance-tracker.log
├── docs/
│   ├── configuration.md
│   ├── import-formats.md
│   └── api-reference.md
├── README.md
└── requirements.txt
```

## Configuration Reference

See [config/settings.yaml](config/settings.yaml) for complete configuration options including:

- Data source settings (Alipay, WeChat, banks)
- Analysis and budget settings
- Report generation options
- Feishu integration
- Email delivery settings

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd finance-tracker

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running Tests

```bash
pytest tests/
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

*Last updated: 2026-02-22*
