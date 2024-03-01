angular.module('operationplandetailapp').directive('devExtremeSchedulerDrv', devExtremeSchedulerDrv);

devExtremeSchedulerDrv.$inject = ['$window', 'gettextCatalog', 'OperationPlan', 'PreferenceSvc'];

function devExtremeSchedulerDrv($window, gettextCatalog, OperationPlan, PreferenceSvc) {
    'use strict';

    var directive = {
        restrict: 'EA',
        scope: {
          displayInfoEditable: '&',
          edited: '&'
          },
        templateUrl: '/static/operationplandetail/editableGantt.html', // Template for the scheduler
        link: linkfunc // Link function for directive logic
    };

    return directive;


    


    function linkfunc($scope, $elem, attrs) {
   



      $(document).ready(function() {
        // Bind mouseenter and mouseleave events to the appointment elements
        $('#scheduler').on('mouseenter', '.appointment-class', function(event) {
            // Extract appointment data from the data attribute
            const appointmentData = $(this).data('appointmentData');
    
            // Show the custom tooltip with appointment details
            showCustomTooltip(appointmentData, event.pageX, event.pageY);
        }).on('mouseleave', '.appointment-class', function() {
            // Hide the custom tooltip when mouse leaves the appointment
            hideCustomTooltip();
        });
    });
    
    function showCustomTooltip(appointmentData, x, y) {
        const tooltipContent = ` 
            Name: ${appointmentData.text}<br>
            Start Date: ${appointmentData.startDate.toLocaleString()}<br>
            End Date: ${appointmentData.endDate.toLocaleString()}<br>
            Resource: ${appointmentData.resource}<br>
            Item: ${appointmentData.item}<br>
            Quantity: ${appointmentData.quantity}<br>
            Delay: ${appointmentData.delay}<br>
            Status: ${appointmentData.status}<br>
            Reference: ${appointmentData.reference}<br>
        `;
    
        // Update the content of the custom tooltip
        $('#customTooltip').html(tooltipContent);
    
        // Position the tooltip near the mouse cursor
        $('#customTooltip').css({
            left: x + 10 + 'px', // Add 10px offset to prevent tooltip from overlapping mouse cursor
            top: y + 10 + 'px' // Add 10px offset to prevent tooltip from overlapping mouse cursor
        });
    
        // Show the custom tooltip
        $('#customTooltip').show();
    }
    
    function hideCustomTooltip() {
        // Hide the custom tooltip
        $('#customTooltip').hide();
    }

      // A place to handle the updating of the data and component rendering
      $scope.$watch('tasks', function () {
      });

      function createTooltip(data) {
        const tooltip = $('<div class="dx-tooltip-appointment-item">');
    
        // Extract resource color using resourceId
        const resource = uniqueResources.find(resource => resource.id === data.appointmentData.resource);
        const markerColor = resource ? resource.color : '#337ab7';
    
        const markerBody = $('<div class="dx-tooltip-appointment-item-marker-body">').css('background', markerColor);
        const marker = $('<div class="dx-tooltip-appointment-item-marker">').append(markerBody);
    
        const content = $('<div class="dx-tooltip-appointment-item-content">')
            .append($('<div class="dx-tooltip-appointment-item-content-subject">').text(data.appointmentData.text))
            .append($('<div class="dx-tooltip-appointment-item-content-date">').text('Start Date: ' + data.appointmentData.startDate.toLocaleString()))
            .append($('<div class="dx-tooltip-appointment-item-content-date">').text('End Date: ' + data.appointmentData.endDate.toLocaleString()))
            .append($('<div class="dx-tooltip-appointment-item-content-date">').text('Resource: ' + resource.text))
            .append($('<div class="dx-tooltip-appointment-item-content-date">').text('Item: ' + data.appointmentData.item))
            .append($('<div class="dx-tooltip-appointment-item-content-date">').text('Quantity: ' + data.appointmentData.quantity))
            .append($('<div class="dx-tooltip-appointment-item-content-date">').text('Delay: ' + data.appointmentData.original.inventory_status))
            .append($('<div class="dx-tooltip-appointment-item-content-date">').text('Status: ' + data.appointmentData.status))
            .append($('<div class="dx-tooltip-appointment-item-content-date">').text('Reference: ' + data.appointmentData.reference));
    
        tooltip.append(marker);
        tooltip.append(content);
    
        return tooltip;
    }
    

        function formatInventoryStatus(opplan) {

            if (opplan.color === undefined || opplan.color === '')
              return [undefined, ""];
            var thenumber = parseInt(opplan.color);
        
            if (opplan.inventory_item || opplan.leadtime) {
              if (!isNaN(thenumber)) {
                if (thenumber >= 100 && thenumber < 999999)
                  return ["rgba(0,128,0,0.5)", Math.round(opplan.computed_color) + "%"];
                else if (thenumber === 0)
                  return ["rgba(255,0,0,0.5)", Math.round(opplan.computed_color) + "%"];
                else if (thenumber === 999999)
                  return [undefined, ""];
                else
                  return ["rgba(255," + Math.round(thenumber / 100 * 255) + ",0,0.5)", Math.round(opplan.computed_color) + "%"];
              }
            } else {
              var thedelay = Math.round(parseInt(opplan.delay) / 8640) / 10;
              if (isNaN(thedelay))
                thedelay = Math.round(parseInt(opplan.operationplan__delay) / 8640) / 10;
              if (parseInt(opplan.criticality) === 999 || parseInt(opplan.operationplan__criticality) === 999)
                return [undefined, ""];
              else if (thedelay < 0)
                return ["rgba(0,128,0,0.5)", (-thedelay) + ' ' + gettext("days early")];
              else if (thedelay === 0)
                return ["rgba(0,128,0,0.5)", gettext("on time")];
              else if (thedelay > 0) {
                if (thenumber > 100 || thenumber < 0)
                  return ["rgba(255,0,0,0.5)", thedelay + ' ' + gettext("days late")];
                else
                  return ["rgba(255," + Math.round(thenumber / 100 * 255) + ",0,0.5)", thedelay + ' ' + gettext("days late")];
              }
            }
            return [undefined, ""];
          };

    function findOperationPlan(ref) {
        if (ref === null) return null;
        return $scope.ganttoperationplans.rows ?
            $scope.ganttoperationplans.rows.find(e => { return e.operationplan__reference == ref; }) :
            null;
        }
        $scope.findOperationPlan = findOperationPlan;




        $(function () {

            var url = (location.href.indexOf("#") != -1 ? location.href.substr(0, location.href.indexOf("#")) : location.href) +
                (location.search.length > 0 ? "?format=gantt&pagesize=1000" : "?format=gantt&pagesize=1000");

            // Make AJAX request
            
            $.ajax({
                url: url,
                method: 'GET',
                dataType: 'json',
                success: function (response) {



                    // Extract unique resources from data
                    const uniqueResources = Array.from(new Set(response.rows.map(row => row.resource))).map(resourceText => {
                        return {
                            text: resourceText,
                            id: Math.floor(Math.random() * 1000), // Assign random integer IDs
                            color: '#081a45' // Generate a random color
                        };
                    });
                    
            
                    // Map through the tasks to reference resources by their text and assigned IDs
                    const tasks = response.rows.map(row => ({
                        text: row.operationplan__operation__name,
                        startDate: new Date(row.operationplan__startdate),
                        endDate: new Date(row.operationplan__enddate),
                        // Find the resource by its text in uniqueResources and get its assigned ID
                        resource: uniqueResources.find(resource => resource.text === row.resource).id,
                        item: row.operationplan__item__name,
                        quantity: row.operationplan__quantity,
                        delay: row.operationplan__delay,
                        status: row.operationplan__status,
                        reference: parseInt(row.operationplan__reference),
                        original: row,
                        color: "rgb(0, 255, 0)",
                        prevColor: "rgb(0, 255, 0)"
                    }));


                    for (var i = 0; i<tasks.length;i++) {
                        var x = tasks[i].original
                        x.type = x.operationplan__type || x.type || default_operationplan_type;
                        if (x.hasOwnProperty("enddate"))
                          x.enddate = new Date(x.enddate);
                        if (x.hasOwnProperty("operationplan__enddate")) {
                          x.operationplan__enddate = new Date(x.operationplan__enddate);
                          x.enddate = x.operationplan__enddate;
                        }
                        if (x.hasOwnProperty("startdate"))
                          x.startdate = new Date(x.startdate);
                        if (x.hasOwnProperty("operationplan__startdate")) {
                          x.operationplan__startdate = new Date(x.operationplan__startdate);
                          x.startdate = x.operationplan__startdate;
                        }
                        if (x.hasOwnProperty("quantity"))
                          x.quantity = parseFloat(x.quantity);
                        if (x.hasOwnProperty("operationplan__quantity"))
                          x.operationplan__quantity = parseFloat(x.operationplan__quantity);
                        if (x.hasOwnProperty("quantity_completed"))
                          x.quantity_completed = parseFloat(x.quantity_completed);
                        if (x.hasOwnProperty("operationplan__quantity_completed"))
                          x.operationplan__quantity_completed = parseFloat(x.operationplan__quantity_completed);
                        if (x.hasOwnProperty("operationplan__status"))
                          x.status = x.operationplan__status;
                        if (x.hasOwnProperty("operationplan__origin"))
                          x.origin = x.operationplan__origin;
                        [x.color, x.inventory_status] = formatInventoryStatus(x);
                      }

                      $scope.calendarevents = response.rows;
                      $scope.totalevents = response.records;
                      $scope.tasks = tasks

                      var minStartDate;
                      const tasksFromApril2024 = tasks.filter(task => task.startDate >= new Date(2024, 3, 1)); // Month is 0-indexed, so April is 3                     
                      if (tasksFromApril2024.length > 0) {
                          minStartDate = new Date(Math.min(...tasksFromApril2024.map(task => task.startDate)));
                      } else {
                          // If there are no tasks in 2024, set a default date
                          minStartDate = new Date(); // Use current date as default
                      }


                    const screenHeight = window.innerHeight; // Get the height of the screen
                    const schedulerHeightPercentage = 40; // Set the percentage of the screen height you want to use for the scheduler
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
                        scrolling: {
                          mode: 'standard'
                        },
                        onAppointmentUpdating: function (e) {
                            if (e.oldData.resource !== e.newData.resource) {
                                e.cancel = true;
                            } else {

                              console.log(upload)
                            }
                        },


                        onAppointmentClick: function (e) {
                          let reference = e.appointmentData.reference
                          let schedulerInstance = $('#scheduler').dxScheduler('instance')
                          let appointment = e.appointmentData
                          // Tasks with the same reference
                          tasks.forEach(function(same) {
                              if(same.reference === reference) {
                                same.prevColor = same.color
                                same.color = "#081a45"
                              } else {
                                if(same.prevColor!=same.color) {
                                  same.color = same.prevColor
                                }
                              }
                          });

                          // Tasks with at least one same demand
                          const tasksWithSameDemandIndices = tasks.reduce((indices, task, index) => {
                            // Extract the names from demands array of the task
                            const taskDemandNames = task.original.demands.map(demand => demand[1]);
                            // Check if there's at least one name common between task's demands and appointment's demands
                            if (appointment.original.demands.some(appointmentDemand => taskDemandNames.includes(appointmentDemand[1]))) {
                                indices.push(index);
                            }
                            return indices;
                          }, []);
                          

                          // Reset all previous colors to false

                          tasks.forEach(task => {
                            task.border = false
                          });


                          // Update the tasks with the same demand by setting the border property to true
                          tasksWithSameDemandIndices.forEach(index => {                         
                              tasks[index].border = true
                          });

                          // Tasks with at least one same demand
                          schedulerInstance.option("dataSource", tasks)
                          // Preserve the horizontal scroll position after repaint
                          schedulerInstance.repaint()
                          const viewStartDate = schedulerInstance.option('currentViewData.startDate');
                          const viewEndDate = schedulerInstance.option('currentViewData.endDate');          
                          // Check if the appointment's start date is within the visible range
                    
                          // Scroll to the appointment's start date
                          schedulerInstance.scrollTo(appointment.startDate);
                          
                          $scope.$parent.displayInfoEditable(appointment.original)



                          //console.log(upload)
                        },
                        

                       /*   appointmentTooltipTemplate(data) {
                            const tooltip = $('<div class="dx-tooltip-appointment-item">');

                            // Extract resource color using resourceId
                            const resource = uniqueResources.find(resource => resource.id === data.appointmentData.resource);
                            const markerColor = resource ? resource.color : '#337ab7';

                            const markerBody = $('<div class="dx-tooltip-appointment-item-marker-body">').css('background', markerColor);
                            const marker = $('<div class="dx-tooltip-appointment-item-marker">').append(markerBody);

                            const content = $('<div class="dx-tooltip-appointment-item-content">')
                                .append($('<div class="dx-tooltip-appointment-item-content-subject">').text(data.appointmentData.text))
                                .append($('<div class="dx-tooltip-appointment-item-content-date">').text('Start Date: ' + data.appointmentData.startDate.toLocaleString()))
                                .append($('<div class="dx-tooltip-appointment-item-content-date">').text('End Date: ' + data.appointmentData.endDate.toLocaleString()))
                                .append($('<div class="dx-tooltip-appointment-item-content-date">').text('Resource: ' + resource.text))
                                .append($('<div class="dx-tooltip-appointment-item-content-date">').text('Item: ' + data.appointmentData.item))
                                .append($('<div class="dx-tooltip-appointment-item-content-date">').text('Quantity: ' + data.appointmentData.quantity))
                                .append($('<div class="dx-tooltip-appointment-item-content-date">').text('Delay: ' + data.appointmentData.original.inventory_status))
                                .append($('<div class="dx-tooltip-appointment-item-content-date">').text('Status: ' + data.appointmentData.status))
                                .append($('<div class="dx-tooltip-appointment-item-content-date">').text('Reference: ' + data.appointmentData.reference));

                            tooltip.append(marker);
                            tooltip.append(content);

                            // Prevent default action when clicking on the tooltip
                            tooltip.on('click', function (event) {
                                event.stopPropagation();
                            });
                           
                            $scope.$parent.displayInfoEditable(data.appointmentData.original);
                            return tooltip;
                        }, */
                      
                        appointmentTemplate(model) { 
                          let color = model.appointmentData.color; // Assuming 'color' is a property in your appointment data
                          let appointment = model.appointmentData;

                          var borderStyle = ""
                          if(appointment.border) {
                              borderStyle = '2px solid #081a45'
                          } else {
                              borderStyle = 'none'
                          }
                          // Store the appointment data as a data attribute on the appointment element
                          const appointmentElement = $(`<div class='appointment-class' title = '' style='width:100%;border: ${borderStyle};height:100%;background: ${color}'></div>`);
                          appointmentElement.data('appointmentData', appointment); // Store appointment data
                          appointmentElement.appendTo('#scheduler'); // Append appointment element to scheduler
                      
                          return appointmentElement;
                      }
                      
                    }); 
                },
                error: function () {

                }
            });
        });
    }
}
