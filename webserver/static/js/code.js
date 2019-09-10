$(document).ready(function() { 
	socketio_client();
});

//SocketIO rotes
function socketio_client() {
    
    //Connect to socketIO server
    var scheme = window.location.protocol == "https:" ? 'wss://' : 'ws://';
    var webSocketUri =  scheme + window.location.hostname + (location.port ? ':'+location.port: '');
    var socket = io.connect(webSocketUri, {transports: ['websocket']});
	
    //Connection event
	socket.on('connect', function() {
		socket.emit('new_client');
	});
    
    //Fan event
	socket.on('fan', function(state) {
		var obj = JSON.parse(state)
		document.getElementById('fan_state').value = obj["fan"];
	});
	
    //Transmission mode event
	socket.on('mode', function(state) {
		var obj = JSON.parse(state)
		document.getElementById('mode').value = obj["mode"];
	});
	
    //Temperature threshold event
	socket.on('threshold', function(temp) {
		var obj = JSON.parse(temp)
		document.getElementById('threshold').value = obj["threshold"];
	});

	//Environmental temperature event
	socket.on('env_temp', function(data) {
		var obj = JSON.parse(data)
		document.getElementById('env_temp').value = obj["temp"];
		document.getElementById('env_temp_timestamp').value = obj["timestamp"];
	});
	
    //Image event
	socket.on('camara', function(data) {
		var obj = JSON.parse(data)
		document.getElementById('max_temp').value = obj["temp_max"]/10;
		document.getElementById('min_temp').value = obj["temp_min"]/10;
		document.getElementById('image_timestamp').value = obj["timestamp"];
	});
	
    //Image event
	socket.on('image', function(data) {
		var blob = new Blob( [ data ], { type: "image/jpeg" } );
		var urlCreator = window.URL || window.webkitURL;
		var imageUrl = urlCreator.createObjectURL( blob );
		document.getElementById("image").src = imageUrl;
	});
	
    //Downlink event
	socket.on('downlink', function(data) {
		var obj = JSON.parse(data)
		alert(obj["msg"]);
	});
	
}

//HTTP route for sending downlink request
function change_parameters() {

	//Get current values
	var current_fan = document.getElementById('fan_state').value;
	var current_mode = document.getElementById('mode').value;
	var current_threshold = parseInt(document.getElementById('threshold').value);
	
	//Get wanted values
	var fan = document.getElementById("fan_select").options[document.getElementById("fan_select").selectedIndex].value;
	var mode = document.getElementById("mode_select").options[document.getElementById("mode_select").selectedIndex].value;
	var threshold = parseInt(document.getElementById('threshold_input').value);
	
	//Check if at least one value is different
	if (current_fan != fan || current_mode != mode || current_threshold != threshold) {
		
		$.ajax({
			url: "/request",
			type: "POST",
			contentType: "application/json",
			data: JSON.stringify({	'fan': fan,
									'mode' : mode,
									'threshold': threshold
									}),
			success: function(result) {
				
				//Check if downlink request was accepted
				if (result["success"]) {
					alert("Downlink was requested!");
				} else {
					alert(result["msg"]);				
				}		
			}
		})
	} else {
		alert("Setup parameters are equal than current parameters");
	}
}	