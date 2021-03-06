angular.module("myApp", ['ngRoute', 'gettext', ])

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

.config(function($routeProvider, $locationProvider) {
    $locationProvider.hashPrefix('');
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

.directive('vehicleLockState', function($q, $log, $http) {
    return {
        restrict : "A",
        templateUrl: '/static/vehicle_lock_state.html',
        scope: {
            vehicleState: '=',
        },
    }
})
.directive('vehicleActions', function($q, $log, $http) {
    return {
        restrict : "A",
        templateUrl: '/static/vehicle_actions.html',
        scope: {
            vehicleState: '=',
            vehicleLockCallback: '&',
            vehicleOpenFrunkCallback: '&',
        },
        link: function($scope, $elem, $attr) {
            $scope.vehicleLock = function() {
                $scope.vehicleLockCallback({});
            };
            $scope.vehicleOpenFrunk = function() {
                $scope.vehicleOpenFrunkCallback({});
            };
        },
    }
})
.directive('nearbyCharger', function($q, $log, $http) {
    return {
        restrict : "A",
        templateUrl: '/static/nearby_charger.html',
        scope: {
            charger: '=',
            navigationRequestCallback: '&'
        },
        link: function($scope, $elem, $attr) {
            $scope.responseResult = "";

            $scope.navigationRequest = function(charger) {
                var url = $scope.navigationRequestCallback({});
                $http.post(url, charger.location).then(function successCallback(response) {
                    $scope.responseResult = 'success';
                  }, function errorCallback(response) {
                    $log.error(response);
                    $scope.responseResult = 'error';
                });
            };
        },
    }
})

.controller('navController', function($scope, $location, $log, gettextCatalog) {
    $scope.defaultLang = 'de';
    $scope.userAgentLanguages = config['userAgentLanguages'];
    $scope.dateTimeFormats = {
        'en': 'MMM d, y HH:mm',
        'de': 'd. MMM, y HH:mm',
        'fr': 'd. MMM, y HH:mm',
    };

    $scope.lang = $scope.defaultLang;
    $scope.dateTimeFormat = $scope.dateTimeFormats[$scope.lang];

    $scope.switchLanguage = function(lang) {
        $scope.lang = lang;
        $scope.dateTimeFormat = $scope.dateTimeFormats[$scope.lang];
        gettextCatalog.setCurrentLanguage(lang);
    };
    var supportedLanguages = {'de': true, 'en': true, 'fr': true, 'el': true};
    var userLanguages = config['userAgentLanguages'].filter(function(l) { return l in supportedLanguages; })
    $log.info("Auto-detected language userAgentLanguages=", config['userAgentLanguages'], ", userLanguages=", userLanguages);
    if (userLanguages.length > 0) {
        $scope.switchLanguage(userLanguages[0]);
    } else {
        $scope.switchLanguage($scope.defaultLang);
    }
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
    $scope.hvacLoading = false;
    $scope.hvacError = false;

    function loadInfo() {
        if ($scope.hvacLoading) {
            return;
        }
        $http.get('/rental/api/' + code).then(function successCallback(response) {
            var rental = response.data.rental;
            //rental.start = moment(rental.start);
            //rental.end = moment(rental.end);
            $scope.rental = rental;

            if ($scope.rental.isActive) {
                setVehicleState(response.data.vehicleState);

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
          }, function errorCallback(response) {
            $log.error(response);
        });
    };

    function getOpenDoorsOrTrunks(vehicleState) {
        var items = [];
        if (vehicleState.trunksOpen.front) {
            items.push("Frunk");
        }
        if (vehicleState.trunksOpen.rear) {
            items.push("Trunk");
        }
        if (vehicleState.doorsOpen.frontLeft) {
            items.push("Door front left");
        }
        if (vehicleState.doorsOpen.frontRight) {
            items.push("Door front right");
        }
        if (vehicleState.doorsOpen.rearLeft) {
            items.push("Door rear left");
        }
        if (vehicleState.doorsOpen.rearRight) {
            items.push("Door rear right");
        }
        return items;
    }

    function setVehicleState(vehicleState) {
        vehicleState.timestamp = moment(vehicleState.timestamp).toDate();
        vehicleState.openDoorsOrTrunks = getOpenDoorsOrTrunks(vehicleState);
        $scope.vehicleState = vehicleState;
    }

    function setClimateState(climateState) {
        climateState.driverTempSetting = Math.round(climateState.driverTempSetting*2)/2;
        $scope.climateState = climateState;
    }

    $scope.vehicleOpenFrunk = function() {
        $scope.hvacLoading = true;
        $http.post('/rental/api/' + code + '/vehicleOpenFrunk').then(function successCallback(response) {
            setVehicleState(response.data.vehicleState);
            $scope.hvacLoading = false;
          }, function errorCallback(response) {
            $log.error(response);
            $scope.hvacLoading = false;
        });
    }
    $scope.vehicleLock = function() {
        $scope.hvacLoading = true;
        $http.post('/rental/api/' + code + '/vehicleLock').then(function successCallback(response) {
            setVehicleState(response.data.vehicleState);
            $scope.hvacLoading = false;
          }, function errorCallback(response) {
            $log.error(response);
            $scope.hvacLoading = false;
        });
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
        $scope.hvacLoading = true;
        $http.post('/rental/api/' + code + '/hvac/temperature/' + (10 * $scope.climateState.driverTempSetting)).then(function successCallback(response) {
            setClimateState(response.data.climateState);
            $scope.hvacLoading = false;
            $scope.hvacError = false;
          }, function errorCallback(response) {
            $log.error(response);
            $scope.hvacLoading = false;
            $scope.hvacError = true;
        });
    };

    $scope.hvacStartStop = function() {
        // md-switch triggers first onchange before updating the model -> invert model current value
        var startStop = !$scope.climateState.autoConditioningOn ? 'hvacStart' : 'hvacStop';
        $scope.hvacLoading = true;
        $http.post('/rental/api/' + code + '/' + startStop).then(function successCallback(response) {
            setClimateState(response.data.climateState);
            $scope.hvacLoading = false;
            $scope.hvacError = false;
          }, function errorCallback(response) {
            $log.error(response);
            $scope.hvacLoading = false;
            $scope.hvacError = true;
        });
    };

    $scope.showNearByChargingStations = function() {
        $scope.nearbyChargingVisible = true;
        $http.get('/rental/api/' + code + '/nearbyCharging').then(function successCallback(response) {
            $scope.nearbyChargers = response.data;
          }, function errorCallback(response) {
            $log.error(response);
        });
    };
    $scope.hideNearByChargingStations = function() {
        $scope.nearbyChargingVisible = false;
    };
    $scope.getNavigationRequest = function() {
        return '/rental/api/' + code + '/navigationRequest';
    };

    function startUpdate() {
        $scope.intervalUpdate = $interval(function() {
            loadInfo();
        }, 10 * 1000);
    };

    $scope.stopUpdate = function() {
        if (angular.isDefined($scope.intervalUpdate)) {
            $interval.cancel($scope.intervalUpdate);
            $scope.intervalUpdate = undefined;
        }
    };

    $scope.$on('$destroy', function() {
      $scope.stopUpdate();
    });

    startUpdate();
    loadInfo();
})

;
