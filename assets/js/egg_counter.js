document.getElementById('eggForm').addEventListener('submit', function(e) {
    e.preventDefault();

    var chickenName = document.getElementById('nameOfChicken').value;
    var timeOfDay = document.getElementById('timeOfDay').value;
    var eggDate = document.getElementById('eggDate').value;
    var myModal = new bootstrap.Modal(document.getElementById('eggModal'));
    
    fetch('/egg_totals/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ chickenName: chickenName, timeOfDay: timeOfDay, eggDate: eggDate }),
    })
    .then(response => {
        console.log(response)
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            Object.keys(data.flock).forEach(chicken => {
                var eggTotalElement = document.getElementById(chicken + '-egg-total');
                if (eggTotalElement) {
                    eggTotalElement.textContent = data.flock[chicken].egg_total;
                }
                myModal.hide();
            });
        }
    })
    .catch((error) => {
        console.error('Error:', error);
    });
});
