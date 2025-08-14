# UPI Financial Manager

A modern, interactive dashboard for analyzing UPI and bank transaction data with automatic merchant extraction, categorization, and insightful visualizations.

## Features

- **📊 Smart Data Processing**: Automatically detects and processes various bank statement formats (CSV, XLSX, TXT)
- **🏪 Merchant Extraction**: Intelligently extracts merchant names from UPI transaction descriptions
- **📈 Interactive Visualizations**: Time series charts, category breakdowns, and merchant analysis
- **✏️ Editable Categories**: Directly edit transaction categories in the interactive table
- **🔍 Advanced Filtering**: Search, date range filtering, and real-time data exploration
- **💾 Export Options**: Download processed data in CSV or Excel format
- **🎨 Modern UI**: Clean, professional interface with responsive design

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the dashboard:
   ```bash
   streamlit run dashboard.py
   ```

2. Upload your bank statement file (CSV, XLSX, or TXT format)

3. The dashboard will automatically:
   - Detect date, narration, and amount columns
   - Extract merchant names from transaction descriptions
   - Categorize transactions as Debit/Credit
   - Display interactive charts and insights

4. Use the sidebar to:
   - Filter by date range
   - Search across all fields
   - Toggle chart visibility

5. Edit categories directly in the table by clicking on category cells

6. Download your processed data using the export buttons

## Supported File Formats

The dashboard can handle various bank statement formats:

- **CSV files**: Standard comma-separated values
- **Excel files**: .xlsx and .xls formats
- **Text files**: Tab or space-separated data

## Column Detection

The dashboard automatically detects common column names:

- **Date columns**: "Date", "Txn Date", "Value Date"
- **Description columns**: "Narration", "Description", "Remarks", "Particulars"
- **Amount columns**: "Amount", "Amt", "Debit", "Credit", "Withdraw", "Deposit"

## Merchant Extraction

The system uses advanced regex patterns to extract merchant names from UPI transaction descriptions:

- `UPI-MERCHANT_NAME-@BANK-REF-UPI`
- `REV-UPI-REF-MERCHANT@BANK-REF-UPI` (reversals)
- `FT-REF-ACCOUNT - MERCHANT - DESCRIPTION` (fund transfers)
- Various other UPI and banking formats

## Features in Detail

### Interactive Table
- Sort, filter, and search transactions
- Edit categories inline
- Pagination for large datasets
- Multi-row selection

### Analytics Dashboard
- **KPIs**: Total spent, total credit, net balance
- **Time Series**: Daily transaction trends
- **Merchant Analysis**: Top merchants by transaction value
- **Category Breakdown**: Pie chart of spending by category
- **Largest Transactions**: Quick view of high-value transactions

### Data Export
- CSV format for spreadsheet applications
- Excel format with proper formatting
- Preserves all edits and categorizations

## Example Use Cases

1. **Personal Finance Tracking**: Upload monthly bank statements to track spending patterns
2. **Business Expense Analysis**: Categorize business transactions for accounting
3. **UPI Transaction Analysis**: Understand spending habits and merchant preferences
4. **Financial Reporting**: Generate reports for budgeting and financial planning

## Tips for Best Results

1. **Clean Data**: Ensure your bank statement has clear column headers
2. **Consistent Format**: Use the same bank statement format for consistent results
3. **Regular Updates**: Process statements regularly for better trend analysis
4. **Category Management**: Use consistent category names for better reporting

## Troubleshooting

- **File Upload Issues**: Ensure your file is in a supported format and not corrupted
- **Column Detection Problems**: Check that your file has clear column headers
- **Merchant Extraction**: Some complex transaction descriptions may need manual categorization
- **Performance**: For very large files (>10,000 rows), consider splitting into smaller chunks

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve the dashboard.

## License

This project is open source and available under the MIT License.