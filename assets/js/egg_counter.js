document.addEventListener('DOMContentLoaded', function() {
    const myModal = new bootstrap.Modal(document.getElementById('eggModal'), {
        keyboard: false // Prevent closing with keyboard for consistency
    });
    
    document.getElementById('eggForm').addEventListener('submit', function(e) {
        e.preventDefault();
    
        const chickenName = document.getElementById('nameOfChicken').value;
        const timeOfDay = document.getElementById('timeOfDay').value;
        const eggDate = document.getElementById('eggDate').value;
        const latestEggDateElement = document.getElementById(chickenName + '-egg-latest');

        // Format today's date as 'YYYY-MM-DD'
        const today = new Date().toISOString().split('T')[0]; 

        if (latestEggDateElement) {
            let latestEggDate = latestEggDateElement.textContent;
            
            // Update the DOM with the new egg date if it's more recent than the latest egg date or if latest egg date is not set
            if (!latestEggDate || new Date(eggDate) > new Date(latestEggDate)) {
                latestEggDateElement.textContent = eggDate;
            }
        }

        // Check if eggDate is today's date before incrementing 'egg-today'
        if (eggDate === today) {
            const eggTodayElement = document.getElementById(`${chickenName}-egg-today`);
            if (eggTodayElement) {
                let eggTodayCount = parseInt(eggTodayElement.textContent, 10) + 1;
                eggTodayElement.textContent = eggTodayCount; // Update DOM
            }
        }
        
        // Always increment 'egg-week', 'egg-month', 'egg-total'
        ['egg-week', 'egg-month', 'egg-total'].forEach(type => {
            const elementId = `${chickenName}-${type}`;
            const element = document.getElementById(elementId);
            if (element) {
                let count = parseInt(element.textContent, 10) + 1;
                element.textContent = count; // Update DOM
            }
        });

        fetch('/egg_totals/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({chickenName, timeOfDay, eggDate})
        })
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                myModal.hide(); // Hide modal if update is successful
            } else {
                throw new Error('Update was not successful');
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    });
});
