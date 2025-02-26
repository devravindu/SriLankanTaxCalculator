import os
from flask import Flask, render_template, request, jsonify, send_file
import weasyprint
from tempfile import NamedTemporaryFile
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

# Tax brackets for local earners (LKR)
LOCAL_TAX_BRACKETS = [
    (1800000, 0),
    (1000000, 0.06),
    (500000, 0.18),
    (500000, 0.24),
    (float('inf'), 0.36)
]

# Tax brackets for foreign earners (LKR)
FOREIGN_TAX_BRACKETS = [
    (1800000, 0),
    (1000000, 0.06),
    (float('inf'), 0.15)
]

def calculate_tax(annual_income, is_foreign):
    """Calculate tax based on income and earner type."""
    brackets = FOREIGN_TAX_BRACKETS if is_foreign else LOCAL_TAX_BRACKETS
    total_tax = 0
    remaining_income = annual_income
    breakdown = []

    for bracket_limit, rate in brackets:
        if remaining_income <= 0:
            break

        taxable_amount = min(remaining_income, bracket_limit)
        tax_for_bracket = taxable_amount * rate

        breakdown.append({
            'bracket_limit': bracket_limit,
            'rate': rate * 100,
            'taxable_amount': taxable_amount,
            'tax': tax_for_bracket
        })

        total_tax += tax_for_bracket
        remaining_income -= taxable_amount

    return total_tax, breakdown

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json()
        monthly_income = float(data['monthlyIncome'])
        earner_type = data['earnerType']
        exchange_rate = float(data.get('exchangeRate', 320))  # Default exchange rate

        # Convert to LKR if foreign earner
        if earner_type == 'foreign':
            monthly_income = monthly_income * exchange_rate

        annual_income = monthly_income * 12
        total_tax, breakdown = calculate_tax(annual_income, earner_type == 'foreign')
        monthly_tax = total_tax / 12

        return jsonify({
            'annualIncome': annual_income,
            'annualTax': total_tax,
            'monthlyTax': monthly_tax,
            'breakdown': breakdown,
            'success': True
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    try:
        data = request.get_json()

        # Create HTML for PDF
        html = render_template(
            'pdf_template.html',
            datetime=datetime,  # Pass datetime module to template
            earner_type=data['earnerType'],
            monthly_income=data['monthlyIncome'],
            annual_income=data['annualIncome'],
            monthly_tax=data['monthlyTax'],
            annual_tax=data['annualTax'],
            breakdown=data['breakdown'],
            exchange_rate=data.get('exchangeRate')
        )

        # Generate PDF
        pdf = weasyprint.HTML(string=html).write_pdf()

        # Create a temporary file to store the PDF
        with NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(pdf)
            temp_file_path = temp_file.name

        return send_file(
            temp_file_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='tax_calculation.pdf'
        )
    except Exception as e:
        app.logger.error(f"PDF generation error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)