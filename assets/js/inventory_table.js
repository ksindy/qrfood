function searchTable() {
  var input, filter, table, tr, txtValue;
  input = document.getElementById("searchInput");
  filter = input.value.toUpperCase();
  table = document.querySelector(".table tbody");
  tr = table.getElementsByTagName("tr");

  for (var i = 0; i < tr.length; i++) {
    // Assuming the item's name is in the first cell, adjust if necessary
    td = tr[i].cells[0]; 
    if (td) {
      txtValue = td.textContent || td.innerText;
      if (txtValue.toUpperCase().indexOf(filter) > -1) {
        tr[i].style.display = "";
      } else {
        tr[i].style.display = "none";
      }
    }
  }
}
