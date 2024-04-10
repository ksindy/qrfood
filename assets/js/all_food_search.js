
document.addEventListener('DOMContentLoaded', function () {
    var searchInput = document.getElementById('searchInput');
    searchInput.addEventListener('keyup', function () {
        var searchTerm = searchInput.value.toLowerCase();
        var tableRows = document.querySelectorAll('.table tbody tr');
        tableRows.forEach(function (row) {
            if (row.cells.length > 0) {
                console.log(row.cells[2].textContent.toLowerCase())
                var foodItem = row.cells[0].textContent.toLowerCase(); // Food item is in the first cell
                var location = row.cells[2].textContent.toLowerCase(); // Location is in the third cell
                var match = foodItem.includes(searchTerm) || location.includes(searchTerm);
                row.style.display = match ? '' : 'none';
            } else {
                // If there are no cells, hide the row or handle accordingly
                row.style.display = 'none';
            }
        });
    });
});
