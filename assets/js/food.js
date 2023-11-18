document.addEventListener('DOMContentLoaded', function () {
    var deleteForm = document.getElementById('deleteForm');
    var itemIdInput = document.getElementById('itemIdToDelete');

    // Event listener for delete buttons
    document.querySelectorAll('[data-bs-toggle="modal"]').forEach(function (button) {
        button.addEventListener('click', function () {
            itemIdInput.value = this.getAttribute('data-item-id');
        });
    });

    // Event listener for the modal's confirmation button
    document.getElementById('confirmDelete').addEventListener('click', function () {
        // Update the action attribute of the form
        deleteForm.action = itemIdInput.value + '/consumed';

        // Submit the form
        deleteForm.submit();

        // Close the modal after action
        $('#deleteConfirmationModal').modal('hide');
    });
});
