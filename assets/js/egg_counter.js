document.getElementById('eggForm').addEventListener('submit', function(e) {
    e.preventDefault();

    var chickenName = document.getElementById('nameOfChicken').value;
    var timeOfDay = document.getElementById('timeOfDay').value;
    var eggDate = document.getElementById('eggDate').value;

    fetch('/egg_totals/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ chickenName: chickenName, timeOfDay: timeOfDay, eggDate: eggDate }),
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            // Assuming the server sends back an updated flock object with egg totals
            Object.keys(data.flock).forEach(chicken => {
                var eggTotalElement = document.getElementById(chicken + '-egg-total');
                console.log(eggTotalElement)
                if (eggTotalElement) {
                    eggTotalElement.textContent = data.flock[chicken].egg_total;
                }
            });
        }
        $('#eggModal').modal('hide');
        $('.modal-backdrop').remove(); 
    })
    .catch((error) => {
        console.error('Error:', error);
    });
});
