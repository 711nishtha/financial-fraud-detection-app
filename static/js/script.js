// ===== DOM ELEMENTS =====
const form = document.getElementById('fraudForm');
const resultsSection = document.getElementById('resultsSection');
const resultCard = document.getElementById('resultCard');
const submitBtn = document.getElementById('submitBtn');
const btnText = document.getElementById('btnText');
const btnSpinner = document.getElementById('btnSpinner');

// ===== FORM SUBMISSION HANDLER =====
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Show loading state
    submitBtn.disabled = true;
    btnText.textContent = 'Analyzing...';
    btnSpinner.classList.remove('hidden');
    resultsSection.classList.remove('show');

    // Gather form data
    const formData = {
        amount: parseFloat(document.getElementById('amount').value),
        type: document.getElementById('type').value,
        oldbalanceOrg: parseFloat(document.getElementById('oldbalanceOrg').value),
        newbalanceOrig: parseFloat(document.getElementById('newbalanceOrig').value),
        oldbalanceDest: parseFloat(document.getElementById('oldbalanceDest').value),
        newbalanceDest: parseFloat(document.getElementById('newbalanceDest').value)
    };

    try {
        // Send request to backend
        const response = await fetch('/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Prediction failed');
        }

        // Display results
        displayResults(data, formData);

    } catch (error) {
        alert('Error: ' + error.message);
        console.error('Error:', error);
    } finally {
        // Reset button state
        submitBtn.disabled = false;
        btnText.textContent = 'Analyze Transaction';
        btnSpinner.classList.add('hidden');
    }
});

// ===== DISPLAY RESULTS FUNCTION =====
function displayResults(data, formData) {
    // Determine if fraud or legitimate
    const isFraud = data.prediction === 'Fraud';
    
    // Update card styling
    resultCard.className = 'result-card ' + (isFraud ? 'fraud' : 'legitimate');
    
    // Update icon
    document.getElementById('resultIcon').textContent = isFraud ? '⚠' : '✓';
    
    // Update title and subtitle
    document.getElementById('resultTitle').textContent = isFraud 
        ? 'Potential Fraud Detected' 
        : 'Legitimate Transaction';
    
    document.getElementById('resultSubtitle').textContent = isFraud
        ? 'This transaction shows suspicious patterns'
        : 'Transaction appears safe and legitimate';
    
    // Update confidence meter
    const confidencePercent = (data.confidence * 100).toFixed(2);
    document.getElementById('confidenceValue').textContent = confidencePercent + '%';
    document.getElementById('confidenceFill').style.width = confidencePercent + '%';
    
    // Update risk badge
    const riskBadge = document.getElementById('riskBadge');
    riskBadge.textContent = data.risk_level + ' Risk';
    riskBadge.className = 'risk-badge ' + data.risk_level.toLowerCase();
    
    // Update details
    document.getElementById('transactionId').textContent = data.transaction_id;
    document.getElementById('detailAmount').textContent = '$' + formData.amount.toLocaleString('en-US', {minimumFractionDigits: 2});
    document.getElementById('detailType').textContent = formData.type.replace('_', ' ');
    
    // Show results with animation
    setTimeout(() => {
        resultsSection.classList.add('show');
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
}

// ===== OPTIONAL: INPUT VALIDATION =====
// Add real-time validation feedback
const inputs = document.querySelectorAll('.form-input');
inputs.forEach(input => {
    input.addEventListener('blur', function() {
        if (this.value && parseFloat(this.value) < 0) {
            this.style.borderColor = 'var(--danger)';
            alert('Please enter a positive number');
            this.value = '';
        }
    });
});

// ===== OPTIONAL: CONSOLE LOG FOR DEBUGGING =====
console.log('🔒 Fraud Detection System Loaded');
console.log('✅ Ready to analyze transactions');