

$(function(){

    var url = (location.href.indexOf("#") != -1 ? location.href.substr(0, location.href.indexOf("#")) : location.href) +
    (location.search.length > 0 ? "&format=json" : "?format=json");

    // Make AJAX request
    $.ajax({
        url: url,
        method: 'GET',
        dataType: 'json',
        success: function(response) {

            console.log(response)

            // Extract unique resources from data
            const uniqueResources = Array.from(new Set(response.rows.map(row => row.resource))).map(resourceText => {
                return {
                  text: resourceText,
                  id: Math.floor(Math.random() * 1000), // Assign random integer IDs
                  color: '#' + Math.floor(Math.random() * 16777215).toString(16) // Generate a random color
                };
              });
              
              // Map through the tasks to reference resources by their text and assigned IDs
              const tasks = response.rows.map(row => ({
                text: row.operationplan__operation__name,
                startDate: new Date(row.operationplan__startdate),
                endDate: new Date(row.operationplan__enddate),
                // Find the resource by its text in uniqueResources and get its assigned ID
                resource: uniqueResources.find(resource => resource.text === row.resource).id
              }));

              const tasksFromApril2024 = tasks.filter(task => task.startDate >= new Date(2024, 3, 1)); // Month is 0-indexed, so April is 3
              const minStartDate = new Date(Math.min(...tasksFromApril2024.map(task => task.startDate)));

              $('#scheduler').dxScheduler({
                timeZone: 'America/Los_Angeles',
                dataSource: tasks,
                views: ['timelineDay', 'timelineWeek', 'timelineWorkWeek', 'timelineMonth'],
                currentView: 'timelineMonth',
                currentDate: minStartDate,
                firstDayOfWeek: 0,
                startDayHour: 8,
                endDayHour: 20,
                cellDuration: 60,
                groups: ['resource'],
                resources: [{
                  fieldExpr: 'resource',
                  allowMultiple: false,
                  dataSource: uniqueResources,
                  label: 'Resources',
                }],
                height: 580,
              });

              console.log(tasks)
              console.log(uniqueResources)
        },
        error: function(xhr, status, error) {

        }
    });





        




      });



/* Cancel dragging into another group

$(() => {
  $('#scheduler').dxScheduler({
    // other configurations...
    onAppointmentDragging: function(e) {
      var sourceResourceId = e.itemData.ownerId; // Get the ID of the source resource
      var targetResourceId = e.newResource ? e.newResource.id : null; // Get the ID of the target resource
      if (sourceResourceId !== targetResourceId) {
        e.cancel = true; // Cancel dragging if the source and target resources are different
      }
    },
    // other configurations...
  });
});

*/