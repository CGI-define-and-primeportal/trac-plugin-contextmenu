jQuery(function($){
  $('div.context-menu').live('click blur', function(e) {
    var holder = $(this)
    var menu = $('.ctx-foldable', holder)
    if (e.type == 'click') {
      if (menu.is(':visible')) {
        menu.fadeOut('fast')
      } else {
        menu.fadeIn('fast');
      }
    } else { // blur
      menu.fadeOut('fast')
    }
  })
})
