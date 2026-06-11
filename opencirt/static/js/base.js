document.addEventListener('keydown', function(event) {
    if (event.key === "Tab") {
        event.preventDefault(); // Optional: Prevent default tabbing behavior
        toggleIncidentSidebar();
    }
});

function toggleIncidentSidebar() {
    let sidebar = document.getElementById("incident-sidebar");
    if (sidebar.style.right === "0px") {
        sidebar.style.right = "-350px";
    } else {
        sidebar.style.right = "0px";
        fetchIncidentActions();
    }
}

function fetchIncidentActions() {
    fetch('/get_incident_actions/')
        .then(response => response.json())
        .then(data => {
            let list = document.getElementById("incident-actions-list");
            list.innerHTML = "";
            data.actions.forEach(action => {
                let li = document.createElement("li");
                li.textContent = action;
                list.appendChild(li);
            });
        });
}
