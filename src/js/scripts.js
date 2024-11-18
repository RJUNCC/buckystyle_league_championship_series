// src/js/scripts.js

document.getElementById('prediction-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const playerName = document.getElementById('player-name').value.trim();
    const resultDiv = document.getElementById('result');
    
    if (!playerName) {
        resultDiv.innerHTML = '<p>Please enter a player name.</p>';
        return;
    }
    
    // Show loading state
    resultDiv.innerHTML = '<p>Loading...</p>';
    
    try {
        const response = await fetch('/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
                // 'X-API-KEY': 'your_api_key' // If you implemented API key authentication
            },
            body: JSON.stringify({ player_name: playerName })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            resultDiv.innerHTML = `<p><strong>${data.player_name}</strong> is predicted to score <strong>${data.predicted_fantasy_points}</strong> fantasy points this season.</p>`;
        } else {
            resultDiv.innerHTML = `<p style="color:red;">${data.error}</p>`;
        }
    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = '<p style="color:red;">An error occurred while fetching the prediction.</p>';
    }
});
