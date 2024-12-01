document.addEventListener('DOMContentLoaded', function () {
    const modalAdd = document.getElementById('addIocModal');
    const modalAddBtn = document.querySelector('.button'); // 'Add IoC' button
    const closeBtnAdd = document.querySelector('.close.add-ioc-modal');

    const modalEdit = document.getElementById('editIocModal');
    const closeBtnEdit = document.querySelector('.close.ioc-modal');
    const saveEditButton = document.getElementById('saveEditIoC'); // Add a save button for edit functionality
    const modalType = document.getElementById('modal-ioc-type');
    const modalValue = document.getElementById('modal-ioc-value');
    const modalStatus = document.getElementById('modal-ioc-status');
    const modalDescription = document.getElementById('modal-ioc-description');
    const modalCreatedBy = document.getElementById('modal-ioc-createdby');
    const modalCreatedAt = document.getElementById('modal-ioc-createdat');
    const modalTags = document.getElementById('modal-ioc-tags');
    const modalActions = document.getElementById('modal-ioc-actions');
//    const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;

    let currentIoCId = null; // Track the current IoC being edited


    if (typeof modalAddBtn !== 'undefined' && modalAddBtn) {
        // Open Modal
        modalAddBtn.addEventListener('click', function () {
            modalAdd.style.display = 'block';
            document.getElementById('created_at').value = new Date().toISOString();
    });
    }
    if (typeof closeBtnAdd !== 'undefined' && closeBtnAdd) {
        // Close Modal Add
        closeBtnAdd.addEventListener('click', function () {
            modalAdd.style.display = 'none';
        });
    }

    // Close Modal Edit
    closeBtnEdit.addEventListener('click', function () {
        modalEdit.style.display = 'none';
    });

    window.addEventListener('click', function (event) {
        if (event.target === modalAdd) {
            modalAdd.style.display = 'none';
        }
    });

    window.addEventListener('click', function (event) {
        if (event.target === modalEdit) {
            modalEdit.style.display = 'none';
        }
    });

    // Handle IoC Deletion
    document.querySelectorAll('.delete-ioc').forEach(button => {
        button.addEventListener('click', function (event) {
            event.stopPropagation(); // Prevent click event from propagating to row

            const row = button.closest('tr');
            const iocId = row.dataset.iocId; // Ensure each row has a data-ioc-id attribute
            const incidentId = document.querySelector('.main-content').getAttribute('incident-id');

            if (confirm('Are you sure you want to delete this IoC?')) {
                fetch(`/api/incident/${incidentId}/delete-ioc/`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ ioc_id: iocId })
                })
                .then(response => {
                    if (response.ok) {
                        return response.json();
                    } else {
                        throw new Error('Failed to delete IoC');
                    }
                })
                .then(data => {
                    row.remove(); // Remove the deleted row from the table
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred while deleting the IoC.');
                });
            }
        });
    });

    // Handle IoC Details Display
    document.querySelectorAll('.ioc-item').forEach(item => {
        item.addEventListener('click', function () {
            event.stopPropagation();
            const iocId = this.dataset.iocId;
            const incidentId = document.querySelector('.main-content').getAttribute('incident-id');

            currentIoCId = iocId; // Save the current IoC ID for editing

            fetch(`/api/incident/${incidentId}/get-ioc/${iocId}/`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === "success") {
                        const ioc = data.data;
                        modalType.value = ioc.type;
                        modalValue.value = ioc.value;
                        modalStatus.value = ioc.status;
                        modalDescription.value = ioc.description;
                        modalCreatedBy.textContent = ioc.created_by;
                        modalCreatedAt.textContent = ioc.created_at;

                        modalTags.innerHTML = '';
                        ioc.tags.forEach(tag => {
                            const tagElement = document.createElement('div');
                            tagElement.className = 'tag';
                            tagElement.style.backgroundColor = tag.color;
                            tagElement.innerHTML = `<span class="tag-item-value">#${tag.name}</span>`;
                            modalTags.appendChild(tagElement);
                        });

                        modalActions.innerHTML = '';
                        ioc.actions.forEach(action => {
                            const actionElement = document.createElement('div');
                            actionElement.className = 'action';
                            actionElement.innerHTML = `<span>${action.created_at} - ${action.title} </span>`;
                            modalActions.appendChild(actionElement);
                        });

                        modalEdit.style.display = 'block';
                    } else {
                        console.error('Error:', data.error);
                    }
                })
                .catch(error => {
                    console.error('Error fetching IoC details:', error);
                });
        });
    });

    // Handle IoC Editing
    saveEditButton.addEventListener('click', function () {
        const incidentId = document.querySelector('.main-content').getAttribute('incident-id');

        const updatedIoC = {
            type: modalType.value,
            value: modalValue.value,
            status: modalStatus.value,
            description: modalDescription.value,
        };

        fetch(`/api/incident/${incidentId}/update-ioc/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ ioc_id: currentIoCId, ...updatedIoC }),
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            } else {
                throw new Error('Failed to update IoC');
            }
        })
        .then(data => {
            if (data.status === "success") {
                modalEdit.style.display = 'none';
                // Optionally, refresh the table or update the UI dynamically
            } else {
                console.error('Error updating IoC:', data.error);
                alert('Failed to update the IoC.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while updating the IoC.');
        });
    });
});
