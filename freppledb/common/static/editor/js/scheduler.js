
var startResource = -1
var endResource = -1


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
                  color: '#081a45'  // Generate a random color
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
              const screenHeight = window.innerHeight; // Get the height of the screen
              const schedulerHeightPercentage = 30; // Set the percentage of the screen height you want to use for the scheduler
              const schedulerHeight = (screenHeight * schedulerHeightPercentage) / 100; // Calculate the height of the scheduler control
              $('#scheduler').dxScheduler({
                timeZone: 'America/Los_Angeles',
                dataSource: tasks,
                views: ['timelineDay', 'timelineWeek', 'timelineWorkWeek', 'timelineMonth'],
                currentView: 'timelineMonth',
                currentDate: minStartDate,
                firstDayOfWeek: 0,
                startDayHour: 8,
                maxAppointmentsPerCell: 'unlimited',
                endDayHour: 20,
                cellDuration: 60,
                groups: ['resource'],
                resources: [{
                  fieldExpr: 'resource',
                  allowMultiple: false,
                  dataSource: uniqueResources,
                  label: 'Resources',
                }],
                height: schedulerHeight, // Set the height of the scheduler control

                  onAppointmentUpdating: function (e) {
                    
                    if(e.oldData.resource !== e.newData.resource) {
                      e.cancel = true;
                    }

                  }
                  // other configurations...
                });
      


        },
        error: function(xhr, status, error) {

        }
    });





        




      });




