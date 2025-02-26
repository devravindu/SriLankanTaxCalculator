document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('taxCalculatorForm');
    const resultSection = document.getElementById('resultSection');
    const exchangeRateGroup = document.querySelector('.exchange-rate-group');
    const currencySymbol = document.querySelector('.currency-symbol');
    const generatePDFBtn = document.getElementById('generatePDF');
    
    let lastCalculationData = null;

    // Toggle exchange rate field and currency symbol based on earner type
    document.querySelectorAll('input[name="earnerType"]').forEach(radio => {
        radio.addEventListener('change', function() {
            exchangeRateGroup.style.display = this.value === 'foreign' ? 'block' : 'none';
            currencySymbol.textContent = this.value === 'foreign' ? 'USD' : 'LKR';
        });
    });

    // Form submission handler
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        if (!form.checkValidity()) {
            e.stopPropagation();
            form.classList.add('was-validated');
            return;
        }

        const monthlyIncome = parseFloat(document.getElementById('monthlyIncome').value);
        const earnerType = document.querySelector('input[name="earnerType"]:checked').value;
        const exchangeRate = parseFloat(document.getElementById('exchangeRate').value);

        try {
            const response = await fetch('/calculate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    monthlyIncome,
                    earnerType,
                    exchangeRate
                })
            });

            const data = await response.json();

            if (data.success) {
                lastCalculationData = {
                    ...data,
                    monthlyIncome,
                    earnerType,
                    exchangeRate
                };
                
                displayResults(data, earnerType === 'foreign');
                resultSection.style.display = 'block';
            } else {
                alert('Error calculating tax: ' + data.error);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred while calculating tax');
        }
    });

    // Generate PDF handler
    generatePDFBtn.addEventListener('click', async function() {
        if (!lastCalculationData) return;

        try {
            const response = await fetch('/generate-pdf', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(lastCalculationData)
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'tax_calculation.pdf';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
            } else {
                alert('Error generating PDF');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred while generating PDF');
        }
    });

    function displayResults(data, isForeign) {
        const currency = isForeign ? 'USD' : 'LKR';
        const exchangeRate = isForeign ? parseFloat(document.getElementById('exchangeRate').value) : 1;
        
        document.getElementById('displayMonthlyIncome').textContent = 
            `${currency} ${(data.annualIncome / 12 / (isForeign ? exchangeRate : 1)).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        
        document.getElementById('displayAnnualIncome').textContent = 
            `LKR ${data.annualIncome.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        
        document.getElementById('displayMonthlyTax').textContent = 
            `LKR ${data.monthlyTax.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        
        document.getElementById('displayAnnualTax').textContent = 
            `LKR ${data.annualTax.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    }
});
