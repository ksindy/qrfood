$('#eggModal').on('show.bs.modal', function (event) {
    var button = $(event.relatedTarget); // Button that triggered the modal
    var chickenName = button.data('chicken-name'); // Extract chicken name from data attribute
    console.log(chickenName)
    var modal = $(this);
    modal.find('#modalChickenName').text(chickenName); // Set chicken name in the modal header
    modal.find('#nameOfChicken').val(chickenName); // Set chicken name in the hidden input field
});
