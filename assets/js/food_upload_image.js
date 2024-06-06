document.addEventListener("DOMContentLoaded", function() {
    //if itemId is passed in via url:
    const foodItemMeta = document.querySelector('meta[name="food-item"]');
    const foodItem = foodItemMeta ? JSON.parse(foodItemMeta.getAttribute("content")) : null;
    let itemId;
    if(foodItem) {
        itemId = document.getElementById("hiddenItemId").value = foodItem.id;
    }

    //preview new image in modal
    function previewFile() {
        const preview = document.getElementById('modalImage');
        const file = document.getElementById('imageInput').files[0];
        const reader = new FileReader();
        console.log(preview)
        reader.onload = function (e) {
            // Set the preview image to the file's data URL
            preview.src = e.target.result;
        };

        if (file) {
            reader.readAsDataURL(file);
        }
    }

    // imageInput.addEventListener('change', function() {
    //     handleImageUpload(this.files[0], itemId);
    // });
    document.getElementById('imageInput').addEventListener('change', previewFile);
    const imageInput = document.getElementById('imageInput');
    function handleImageUpload(file, itemId) {
        if (!file) {
            console.error('No file selected for upload');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('itemId', itemId);
        console.log(itemId)

        fetch('/upload-image/', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            console.log('Upload successful', data);
            // Update the modal image or handle the response accordingly
            $('#modal-1').modal('hide');
        })
        .catch(error => {
            console.error('Error uploading image:', error);
        });

        const formData2 = new FormData();
        formData2.append('image_url', "yes");
        formData2.append('item_id', itemId);
        console.log(formData2);
        fetch(`/food/${itemId}/update/`, {
            method: 'POST',
            body: formData2
        })
        .then(response => response.json())
        .then(data => console.log('Response:', data))
        .catch(error => console.error('Error:', error));
    }


    if (foodItem && Object.keys(foodItem).length > 0) {
        populateAndShowModal(foodItem);
    }

    function populateAndShowModal(item) {
        const modalImage = document.getElementById('modalImage');
        const modalFoodName = document.getElementById('modalFoodName');
        const modalFoodLocation = document.getElementById('modalFoodLocation');
        const modalFoodDate = document.getElementById('modalFoodDate');
        const modalExpirationDetails = document.getElementById('modalExpirationDetails');

        // Use a default image if "None" is provided
        console.log(item)
        modalImage.src = item.image_url === 'None' || !item.image_url ? 'https://qr-app-images-dev.s3.us-east-2.amazonaws.com/default_food_photo.jpeg' : item.image_url;
        modalFoodName.value = item.food;
        modalFoodLocation.value = item.location;
        modalFoodDate.value = item.expiration_date;

        // Calculate and display expiration details
        const expirationDate = new Date(item.expiration_date);
        const today = new Date();
        const diffTime = Math.abs(expirationDate - today);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        const years = Math.floor(diffDays / 365);
        let remainingDays = diffDays % 365;
        const months = Math.floor(remainingDays / 30);
        remainingDays = remainingDays % 30;

        modalExpirationDetails.value = `${years} years, ${months} months, ${remainingDays} days until expiration`;

        // Show the modal
        $('#modal-1').modal('show');
    }

    document.querySelectorAll('.item-link').forEach(link => {
        link.addEventListener('click', function(event) {
            event.preventDefault();
            itemId = this.dataset.itemId;
            console.log(this.dataset.itemImage)

            populateAndShowModal({
                id: itemId,
                image_url: this.dataset.itemImage,
                food: this.dataset.itemFood,
                location: this.dataset.itemLocation,
                expiration_date: this.dataset.itemExpiration
            });
        });
    });
        document.getElementById('saveButton').addEventListener('click', function() {
        const file = document.getElementById('imageInput').files[0];
        handleImageUpload(file, itemId);
    });
});
