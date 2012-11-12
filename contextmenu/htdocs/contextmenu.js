jQuery(function($){
  $('div.context-menu').live('click blur', function(e) {
    var holder = $(this)
    var menu = $('.ctx-foldable', holder)
    if (e.type == 'click') {
      if (menu.is(':visible')) {
        menu.fadeOut('fast')
      } else {
        var row = holder.closest('tr')
        var top = row.position().top + row.outerHeight() - 1
        var left = holder.position().left
        var bgColor = row.css('background-color')
        menu.css({top: top, width:'auto',
                  left: left,
                  backgroundColor: bgColor}).show()
      }
    } else { // blur
      menu.fadeOut('fast')
    }
  })
})
