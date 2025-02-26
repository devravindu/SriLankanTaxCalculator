import os
from flask import Flask, render_template, request, jsonify, send_file, session
from flask_babel import Babel, gettext as _
import weasyprint
from tempfile import NamedTemporaryFile
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

# Configure Babel
babel = Babel()
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['LANGUAGES'] = {
    'en': 'English',
    'si': 'සිංහල',
    'ta': 'தமிழ்'
}
babel.init_app(app)

def get_locale():
    try:
        return session.get('language', 'en')
    except Exception as e:
        logger.error(f"Error in locale selection: {str(e)}")
        return 'en'

babel.init_app(app, locale_selector=get_locale)

@app.route('/')
def index():
    try:
        return render_template('index.html', languages=app.config['LANGUAGES'])
    except Exception as e:
        logger.error(f"Error rendering index: {str(e)}")
        return "An error occurred", 500

@app.route('/set-language/<language>')
def set_language(language):
    try:
        if language in app.config['LANGUAGES']:
            session['language'] = language
            return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error setting language: {str(e)}")
    return jsonify({'success': False})

# Tax brackets for local earners (LKR)
LOCAL_TAX_BRACKETS = [
    (1800000, 0),      # First 1.8M: 0%
    (1000000, 0.06),   # Next 1M: 6%
    (500000, 0.18),    # Next 500K: 18%
    (500000, 0.24),    # Next 500K: 24%
    (float('inf'), 0.36)  # Remainder: 36%
]

# Tax brackets for foreign earners (LKR)
FOREIGN_TAX_BRACKETS = [
    (1800000, 0),      # First 1.8M: 0%
    (1000000, 0.06),   # Next 1M: 6%
    (float('inf'), 0.15)  # Remainder: 15%
]

def calculate_tax(annual_income, is_foreign):
    """Calculate tax based on income and earner type."""
    try:
        brackets = FOREIGN_TAX_BRACKETS if is_foreign else LOCAL_TAX_BRACKETS
        total_tax = 0
        remaining_income = annual_income
        breakdown = []
        cumulative_income = 0

        for bracket_limit, rate in brackets:
            if remaining_income <= 0:
                break

            if bracket_limit == float('inf'):
                taxable_amount = remaining_income
            else:
                taxable_amount = min(remaining_income, bracket_limit)

            tax_for_bracket = taxable_amount * rate

            breakdown.append({
                'bracket_limit': bracket_limit if bracket_limit != float('inf') else cumulative_income + remaining_income,
                'rate': rate * 100,
                'taxable_amount': taxable_amount,
                'tax': tax_for_bracket
            })

            total_tax += tax_for_bracket
            remaining_income -= taxable_amount
            cumulative_income += taxable_amount

        app.logger.debug(f"Tax calculation breakdown: {breakdown}")
        return total_tax, breakdown

    except Exception as e:
        app.logger.error(f"Error in calculate_tax: {str(e)}")
        raise

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': _('No data provided')})

        monthly_income = float(data.get('monthlyIncome', 0))
        if monthly_income < 0:
            return jsonify({'success': False, 'error': _('Monthly income cannot be negative')})

        earner_type = data.get('earnerType')
        if earner_type not in ['local', 'foreign']:
            return jsonify({'success': False, 'error': _('Invalid earner type')})

        exchange_rate = float(data.get('exchangeRate', 320))
        if exchange_rate <= 0:
            return jsonify({'success': False, 'error': _('Exchange rate must be positive')})

        if earner_type == 'foreign':
            monthly_income_lkr = monthly_income * exchange_rate
            annual_income = monthly_income_lkr * 12
        else:
            annual_income = monthly_income * 12

        total_tax, breakdown = calculate_tax(annual_income, earner_type == 'foreign')
        monthly_tax = total_tax / 12

        response_data = {
            'annualIncome': annual_income,
            'annualTax': total_tax,
            'monthlyTax': monthly_tax,
            'breakdown': breakdown,
            'success': True
        }

        app.logger.debug(f"Calculation successful: {response_data}")
        return jsonify(response_data)

    except ValueError as e:
        app.logger.error(f"Value error in calculation: {str(e)}")
        return jsonify({'success': False, 'error': _('Invalid numeric input')})
    except Exception as e:
        app.logger.error(f"Unexpected error in calculation: {str(e)}")
        return jsonify({'success': False, 'error': _('An error occurred while calculating tax')})

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    try:
        data = request.get_json()

        html = render_template(
            'pdf_template.html',
            datetime=datetime,
            earner_type=data['earnerType'],
            monthly_income=data['monthlyIncome'],
            annual_income=data['annualIncome'],
            monthly_tax=data['monthlyTax'],
            annual_tax=data['annualTax'],
            breakdown=data['breakdown'],
            exchange_rate=data.get('exchangeRate')
        )

        pdf = weasyprint.HTML(string=html).write_pdf()

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