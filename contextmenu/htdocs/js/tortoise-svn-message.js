$(document).ready(function() {

  $("#tortoise-svn-message-dialog").dialog({
    autoOpen: false,
    width: 600,
    modal: true,
    title: 'Do you have TortoiseSVN installed?',
    buttons: {
      Continue: function(e) {
        // close the dialog
        $(this).dialog("close");
        // continue with the tortoise svn protocol
        window.open($("#browse-with-tortoise").attr("href"), "_self");
        // send an ajax request in the background to set the session attribute
        options = {
          type:"POST",
          data: $("#tortoise-svn-message-form").serialize(),
          url: window.tracBaseUrl + "ajax/tortoise-svn-message"
        }
        $.ajax(options)
      }
    }
  });

  // listen to clicks on the tortoise svn checkout context nav icon 
  // if tortoise-svn-data is false the user needs to be shown the dialog
  if (!tortoise_svn_message) {
    $("#browse-with-tortoise").click(function(e) {
      $("#tortoise-svn-message-dialog").dialog('open');
      e.preventDefault();
    });
  }
});