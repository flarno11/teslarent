angular.module("myApp", ['ngRoute', ]) //'ngMaterial',

/*.config(function($mdThemingProvider) {
  $mdThemingProvider.theme('default')
    .primaryPalette('red')
    .accentPalette('red')
    //.backgroundPalette('blue-grey')
    .dark()
    ;
})
.config(function($mdProgressCircularProvider) {
  $mdProgressCircularProvider.configure({
    progressSize: 20,
  });
})*/
.config(function($httpProvider) {
    $httpProvider.defaults.xsrfCookieName = 'csrftoken';
    $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
})

.config(function($routeProvider) {
    $routeProvider
    .when("/", {
        templateUrl : "/static/codeInput.html",
        controller : "codeInputController"
    })
    .when("/rental/:code", {
        templateUrl : "/static/rental.html",
        controller : "rentalController"
    })
    ;
})

.controller('navController', function($scope, $location, $log) {
})

.controller('codeInputController', function($scope, $q, $log, $location) {
    $scope.code = undefined;

    $scope.submit = function() {
        $log.info("code=" + $scope.code);
        $location.path('/rental/' + $scope.code);
    };
})

.controller('rentalController', function($scope, $http, $log, $location, $routeParams, $interval) {
    var code = $routeParams['code'];

    function loadInfo() {
        $log.debug("loading info...");
        $http.get('/rental/api/' + code).then(function successCallback(response) {
            var rental = response.data.rental;
            //rental.start = moment(rental.start);
            //rental.end = moment(rental.end);
            $scope.rental = rental;

            if ($scope.rental.isActive) {
                $scope.vehicleState = response.data.vehicleState;

                var chargeState = response.data.chargeState;
                chargeState.timeToFullChargeHours = Math.floor(chargeState.timeToFullCharge);
                chargeState.timeToFullChargeMins = chargeState.timeToFullCharge % 1 * 60;
                $scope.chargeState = chargeState;

                var driveState = response.data.driveState;
                driveState.gpsAsOf = moment(response.data.driveState.gpsAsOf).toDate();
                $scope.driveState = driveState;

                setClimateSettings(response.data.climateSettings);
                $scope.uiSettings = response.data.uiSettings;
            }

            $log.debug("loading info... done");
          }, function errorCallback(response) {
            $log.error(response);
        });
    };

    function setClimateSettings(climateSettings) {
        climateSettings.driverTempSetting = Math.round(climateSettings.driverTempSetting*2)/2;
        $scope.climateSettings = climateSettings;
    }

    $scope.hvacSetTemperatureDecrease = function() {
        $scope.climateSettings.driverTempSetting -= 0.5;
        $scope.hvacSetTemperature();
    }
    $scope.hvacSetTemperatureIncrease = function() {
        $scope.climateSettings.driverTempSetting += 0.5;
        $scope.hvacSetTemperature();
    }

    $scope.hvacSetTemperature = function() {
        $http.post('/rental/api/' + code + '/hvac/temperature/' + (10 * $scope.climateSettings.driverTempSetting)).then(function successCallback(response) {
            setClimateSettings(response.data.climateSettings);
          }, function errorCallback(response) {
            $log.error(response);
        });
    };

    $scope.hvacStartStop = function() {
        // md-switch triggers first onchange before updating the model -> invert model current value
        var startStop = !$scope.climateSettings.isAutoConditioning ? 'hvacStart' : 'hvacStop';
        $http.post('/rental/api/' + code + '/' + startStop).then(function successCallback(response) {
            setClimateSettings(response.data.climateSettings);
          }, function errorCallback(response) {
            $log.error(response);
        });
    };

    var intervalUpdate = $interval(function() {
        loadInfo();
    }, 10 * 1000);

    $scope.stopUpdate = function() {
        if (angular.isDefined(intervalUpdate)) {
            $interval.cancel(intervalUpdate);
            intervalUpdate = undefined;
        }
    };

    $scope.$on('$destroy', function() {
      $scope.stopUpdate();
    });

    loadInfo();
})

;
