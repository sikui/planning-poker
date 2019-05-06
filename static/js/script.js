$(document).ready(function(){

  // perform ajax request
  function doRequest(url, method, params) {

    return new Promise(function(resolve, reject) {
      $.ajax({
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        url: url,
        type: method,
        data: JSON.stringify(params),
        dataType: "json"
      }).done(function(data){
        resolve(data);
      }).fail(function(){
        return reject('rejected');
      });
    });
  }

  function addRowsTable(data, tableID) {
    // clear table row
    $("#" + tableID + " tbody").find("tr").remove();
    data.forEach(function (item, index) {
      rowString = '<tr>' +
      '<td>' + item['title'] + '</td>' +
      '<td class="description">' + item['description'] + '</td>';
      if (typeof(item['username']) != "undefined") {
        rowString += '<td>' + item['username'] + '</td>';
      }
      rowString +=
      '<td> <button class="details" data-poll-id="' + item['id'] + '"><i class="fas fa-external-link-alt"></i></i></button> </td>' +
      '<td> <button data-poll-id="' + item['id'] + '" data-toggle="tooltip" data-placement="bottom" title="Copy to Clipboard!"><i class="fas fa-link"></i></button> </td>' +
      + '</tr>';
      $("#" + tableID + " tbody").append(rowString);
    });

    $(".details").on('click', function(){
      loadPollData($(this).attr("data-poll-id"));
      $("#pollDetailsModal").modal('toggle');
    });

    //initialize the tooltip
    $('[data-toggle="tooltip"]').tooltip();
    $('[data-toggle="tooltip"]').on('click', function(){
      copyToCliboard($(this).attr("data-poll-id"));
    });
  }

  function copyToCliboard(poll_id){
    var $temp = $("<input>");
    $("body").append($temp);
    $temp.val(window.location.href.split('?')[0] + "?poll=" + poll_id).select();
    document.execCommand("copy");
    $temp.remove();
    swal({
      title: "Link copied!",
      icon: "success",
      button: false,
      timer: 1500
    });
  }

  // list of user polls
  function loadUserPolls(){
    var token = getAuthToken("user");
    if (token) {
      var url = "/polls/users/" + token
      doRequest(url, "GET").then(function(response) {
        polls = response['data']['polls'];
        addRowsTable(polls,"user-polls")
      });
    }
  }

  // list of today's poll
  function loadTodayPolls(){
    var url = "/polls/list/";
    doRequest(url, "GET").then(function(response) {
      polls = response['data']['polls'];
      addRowsTable(polls, "current-polls");
    });
  }

  // create a POST
  function createPoll(){
    var url = "/polls/"
    var data = {} ;
    data['title'] = $("#pollTitle").val();
    data['description'] =  $("#pollDescription").val();
    data['user_id'] = getAuthToken("user");
    doRequest(url, "POST", data).then(function(response) {
      poll_id = response['data'];
      // close  Modal
      $("#pollModal").modal('toggle');
      swal({
        title: "Poll created!",
        text: "Share with collegues: " + window.location.href.split('?')[0] + "?poll=" + poll_id,
        icon: "success",
        button: "Close",
      });
    });
  }

  // clear create poll form before showing
  $("#pollModal").on('show.bs.modal', function(){
    $('#pollModal form').get(0).reset();
  });

  $("#pollDetailsModal").on('hidden.bs.modal', function(){
    currentPoll = undefined;
  });

  $("#subimt-form").click(function(event) {
    event.preventDefault();
    createPoll();
  });

  function loadPollData(poll_id){
    var url = "/polls/" + poll_id;
    doRequest(url, "GET").then(function(response) {
      details = response['data'];
      if (details['polls'] !== null) {
        $('button[id*=vote-]').removeClass("vote_chosen");
        $('#poll_title').text(details['polls']['title']);
        $('#poll_description').text(details['polls']['description']);
        votes = details['votes']

        loadChartData(votes, typeof currentPoll != "undefined");

        $('button[id*=vote-]').attr("data-poll-id", poll_id);
        loadUserVote(poll_id);
        currentPoll = poll_id;
      } else {
        swal("Ooops!", "Something went wrong :(" , "error");
      }
    });
  }

  function loadUserVote(poll_id){
    url = "/polls/" + poll_id + "/users/" + getAuthToken("user");
    doRequest(url, "GET").then(function(response) {
      $('button[id*=vote-]').removeClass("vote_chosen")
      vote = response['data']['votes'];
      if (vote != null) {
        vote = vote.replace(".", "-");
        // hightlight the user vote for the poll
        $("#vote-" + vote).addClass("vote_chosen");
      }
    });
  }

  $('button[id*=vote-]').on('click', function(){
    // edit vote
    var poll_id =  $(this).attr("data-poll-id");
    var vote= $(this).text();
    var data = {
      "value" : vote
    }
    var url = "polls/" + poll_id + "/users/" + getAuthToken("user") + "/vote";
    doRequest(url, "POST", data).then(function(response) {
      vote = vote.replace(".", "-");
      $('button[id*=vote-]').removeClass("vote_chosen");
      $('button[id=vote-' + vote + ']').addClass("vote_chosen");
    });
  });

  var myBarChart = undefined;
  var currentPoll = undefined;

  function drawData(votes) {
    var ctx = document.getElementById('pollVotes');
    var labels = votes.map(function(e) {
      return e.value;
    });
    var votes = votes.map(function(e) {
      return e.votes;
    });
    myBarChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: '# of Votes',
          data: votes,
          backgroundColor: [
            'rgba(255, 99, 132, 0.2)',
            'rgba(54, 162, 235, 0.2)',
            'rgba(255, 206, 86, 0.2)',
            'rgba(75, 192, 192, 0.2)',
            'rgba(153, 102, 255, 0.2)',
            'rgba(255, 159, 64, 0.2)'
          ],
          borderColor: [
            'rgba(255, 99, 132, 1)',
            'rgba(54, 162, 235, 1)',
            'rgba(255, 206, 86, 1)',
            'rgba(75, 192, 192, 1)',
            'rgba(153, 102, 255, 1)',
            'rgba(255, 159, 64, 1)'
          ],
          borderWidth: 1
        }]
      },
      options: {
        scales: {
          yAxes: [{
            ticks: {
              beginAtZero: true
            }
          }]
        }
      }
    });
  }

// create or
  function loadChartData(votes, updateData){
    if (updateData) {
        var vote = votes.map(function(e) {
          return e.votes;
        });

        myBarChart.data.datasets.forEach((dataset) => {
          dataset.data = vote;
        });
        myBarChart.update(0);
    } else {
      if(myBarChart!=null){
        myBarChart.destroy();
      }
      drawData(votes);
    }
  }

// retrieve "auth token" from cookie
  function getAuthToken(cname){
    var name = cname + "=";
    var decodedCookie = decodeURIComponent(document.cookie);
    var ca = decodedCookie.split(';');
    for(var i = 0; i <ca.length; i++) {
      var c = ca[i];
      while (c.charAt(0) == ' ') {
        c = c.substring(1);
      }
      if (c.indexOf(name) == 0) {
        return c.substring(name.length, c.length);
      }
    }
    return "";
  }

  $("#create-user").click(function(event) {
    event.preventDefault();
    createUser();
  });

  function createUser(){
    var url = "/polls/users/create"
    var data = {
       "username" : $("#username").val()
    }
    doRequest(url, "POST", data).then(function(response) {
        token = response['data']['token'];
        // serve sends an "auth token", stored in a cookie
        if (token) {
          document.cookie = "user=" + token;
          // close dialog
          $("#createUser").modal('toggle');
          swal({
            title: "User created!",
            icon: "success",
            button: "Close",
          });
        }
    });
  }

function checkUser(){
  if (getAuthToken("user") == "") {
    swal(
      "Attention!",
      "Before using the platform, you should create an account.",
      "info"
    )
  }
}

// polling for real time update
  function update(){
    loadTodayPolls();
    loadUserPolls();
    if (typeof currentPoll != "undefined"){
      // update poll details
      loadPollData(currentPoll);
    }
    setTimeout(update, 3000); //  update home page every 3 secs
  }

// use share link
  if (window.location.search != "") { // poll id has been specified
    var poll_id = new URL(location.href).searchParams.get('poll');
    loadPollData(poll_id);
    $("#pollDetailsModal").modal('toggle');
  }

  update();

  checkUser();
});
