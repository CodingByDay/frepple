angular.module('operationplandetailapp').directive('devExtremeSchedulerDrv', devExtremeSchedulerDrv);

devExtremeSchedulerDrv.$inject = ['$window', 'gettextCatalog', 'OperationPlan', 'PreferenceSvc'];

function devExtremeSchedulerDrv($window, gettextCatalog, OperationPlan, PreferenceSvc) {
    'use strict';

    var directive = {
        restrict: 'EA',
        scope: {
            editableGanttSelected: '&'
          },
        templateUrl: '/static/operationplandetail/editableGantt.html', // Template for the scheduler
        link: linkfunc // Link function for directive logic
    };

    return directive;


    


    function linkfunc($scope, $elem, attrs) {

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



        var startResource = -1;
        var endResource = -1;

        $(function () {
            var url = (location.href.indexOf("#") != -1 ? location.href.substr(0, location.href.indexOf("#")) : location.href) +
                (location.search.length > 0 ? "&format=json" : "?format=json");

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
                        reference: row.operationplan__reference,
                        original: row

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
                            if (e.oldData.resource !== e.newData.resource) {
                                e.cancel = true;
                            }
                        },

                        appointmentTooltipTemplate(data, cell) {
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
                                .append($('<div class="dx-tooltip-appointment-item-content-date">').text('Delay: ' + data.appointmentData.delay))
                                .append($('<div class="dx-tooltip-appointment-item-content-date">').text('Status: ' + data.appointmentData.status))
                                .append($('<div class="dx-tooltip-appointment-item-content-date">').text('Reference: ' + data.appointmentData.reference));

                            tooltip.append(marker);
                            tooltip.append(content);

                            // Prevent default action when clicking on the tooltip
                            tooltip.on('click', function (event) {
                                event.stopPropagation();
                            });
                           
                            $scope.$parent.editableGanttSelected(data);


                            return tooltip;
                        }
                    });
                },
                error: function (xhr, status, error) {

                }
            });
        });
    }
}
