jQuery(function($){
  $('div.context-menu').live('click', function(e) {
    var holder = $(this)
    var menu = $('div:first', holder)
    if (menu.is(':visible')) {
      menu.fadeOut('fast')
    } else {
      $('div.context-menu div.ctx-foldable').hide()
      var row = holder.closest('tr')
      var top = row.position().top + row.outerHeight() - 1
      var left = holder.position().left
      var bgColor = row.css('background-color')
      menu.css({top: top,
                left: left,
                backgroundColor: bgColor}).show()
    }
  })
})
