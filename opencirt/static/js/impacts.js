document.addEventListener("DOMContentLoaded", function () {
    const lastSelectedImpact = localStorage.getItem("lastSelectedImpact");

    function triggerClick(element) {
        if (element) {
            setTimeout(() => {
                element.click();
            }, 0); // Small delay to ensure elements are interactive
        }
    }

    // Restore last selected impact or load the first one
    if (lastSelectedImpact) {
        const impactItem = document.querySelector(`.impact-item[data-impact-id='${lastSelectedImpact}']`);
        triggerClick(impactItem);
        localStorage.removeItem("lastSelectedImpact");
    } else {
        const firstImpactItem = document.querySelector(".impact-item");
        triggerClick(firstImpactItem);
    }

    const incidentId = document.getElementById('incident-id').value;
    const csrfToken = document.getElementById('csrf-token').value;
    const title = document.getElementById('title');
    const severity = document.getElementById('severity');
    const status = document.getElementById('status');
    const type = document.getElementById('type');
    const description = document.getElementById('description');
    const external_reference = document.getElementById('external_reference');
    const starting_time = document.getElementById('starting_time');
    const ending_time = document.getElementById('ending_time');
    const saveButton = document.getElementById('saveButton'); // Fix missing variable

    let currentImpact = null;

    function setDropdownValue(id, value) {
        const el = document.getElementById(id);
        if (el) el.value = value;
    }

    // Attach event listeners AFTER ensuring elements exist
    document.querySelectorAll(".impact-item").forEach(row => {
        row.addEventListener("click", function () {
            let impactId = parseInt(this.dataset.impactId, 10);
            
            fetch(`/api/incident/${incidentId}/get-impact/${impactId}/`)
                .then(response => response.json())
                .then(data => {
                    if (data.data) { 
                        let impact = data.data;
                        currentImpact = impactId;
                        title.value = impact.title;
                        description.value = impact.description;
                        external_reference.value = impact.external_reference;
                        starting_time.value = impact.starting_time;
                        ending_time.value = impact.ending_time;

                        setDropdownValue("severity", impact.severity);
                        setDropdownValue("status", impact.status);
                        setDropdownValue("type", impact.type);
                    } else {
                        console.error("Invalid response format:", data);
                    }
                })
                .catch(error => console.error("Error fetching impact:", error));
        });
    });

    // update-impact
    saveButton.addEventListener('click', function () {
        if (!currentImpact) {
            alert("Please select an impact before updating.");
            return;
        }

        const data = {
            id: currentImpact,
            title: title.value,
            description: description.value,
            status: status.value,
            severity: severity.value,
            type: type.value,
            external_reference: external_reference.value,
            starting_time: starting_time.value,
            ending_time: ending_time.value
        };

        fetch(`/api/incident/${incidentId}/update-impact/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ data }),
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            } else {
                throw new Error('Failed to update impact');
            }
        })
        .then(updatedImpact => {
            localStorage.setItem("lastSelectedImpact", currentImpact);
            window.location.reload();
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while updating the impact.');
        });
    });

});