document.addEventListener('DOMContentLoaded', function () {
    var locationSelect = document.getElementById('locationSelect');
    var otherLocationInput = document.getElementById('otherLocation');

    locationSelect.addEventListener('change', function () {
        if (this.value === 'other') {
            otherLocationInput.style.display = 'block';
        } else {
            otherLocationInput.style.display = 'none';
        }
    });
});
