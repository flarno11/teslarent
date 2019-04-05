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
    $scope.debugMode = 'debug' in $routeParams;
    $log.debug($routeParams, $scope.debugMode);

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
                driveState.gpsAsOf = moment(driveState.gpsAsOf).toDate();
                $scope.driveState = driveState;

                setClimateState(response.data.climateState);
                $scope.uiSettings = response.data.uiSettings;
            }

            $log.debug("loading info... done");
          }, function errorCallback(response) {
            $log.error(response);
        });
    };

    function setClimateState(climateState) {
        climateState.driverTempSetting = Math.round(climateState.driverTempSetting*2)/2;
        $scope.climateState = climateState;
    }

    $scope.hvacSetTemperatureDecrease = function() {
        $scope.climateState.driverTempSetting -= 0.5;
        $scope.hvacSetTemperature();
    }
    $scope.hvacSetTemperatureIncrease = function() {
        $scope.climateState.driverTempSetting += 0.5;
        $scope.hvacSetTemperature();
    }

    $scope.hvacSetTemperature = function() {
        $http.post('/rental/api/' + code + '/hvac/temperature/' + (10 * $scope.climateState.driverTempSetting)).then(function successCallback(response) {
            setClimateState(response.data.climateState);
          }, function errorCallback(response) {
            $log.error(response);
        });
    };

    $scope.hvacStartStop = function() {
        // md-switch triggers first onchange before updating the model -> invert model current value
        var startStop = !$scope.climateState.autoConditioningOn ? 'hvacStart' : 'hvacStop';
        $http.post('/rental/api/' + code + '/' + startStop).then(function successCallback(response) {
            setClimateState(response.data.climateState);
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
