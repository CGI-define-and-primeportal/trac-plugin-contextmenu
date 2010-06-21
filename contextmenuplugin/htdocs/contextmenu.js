jQuery(function($){
  $('div.context-menu').live('click', 
    function(e) {
      var holder = $(this)
      var ul = $('ul', holder)
      if (ul.is(':visible')) {
        ul.hide()
      } else {
        var p = holder.position()
        ul.css('top', p.top + holder.height).css('left', (p.left + holder.width()) - ul.width()).show()
      }  
    }
  )
})
