jQuery(function($){
  $('div.context-menu').live('click', function(e) {
    var holder = $(this)
    var menu = $('div:first', holder)
    function findScrollTop(e) {
      var s = e.scrollTop()
      if (s) return s
      if (e.parent().length)
        return findScrollTop(e.parent())
      return 0
    }
    if (menu.is(':visible')) {
      menu.fadeOut('fast')
    } else {
      $('div.context-menu div.ctx-foldable').hide()
      var row = holder.closest('tr')
      // Add scrolltop if we're in a scrolling div
      var scrollTop = findScrollTop($(this))
      var top = row.position().top + row.outerHeight() - 1 + scrollTop
      var left = holder.position().left
      var bgColor = row.css('background-color')
      menu.css({top: top,
                left: left,
                backgroundColor: bgColor}).show()
    }
  })
})
