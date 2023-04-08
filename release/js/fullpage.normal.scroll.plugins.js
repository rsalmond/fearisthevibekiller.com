
/* ==============================================
FULL PAGE VERSION 2 - NORMAL SCROLL PLUGINS
=============================================== */	

	$('#fullpage').fullpage({
		sectionsColor: ['#000', '#000', '#000', '#000', '#000', '#fff'],
		navigation: true,
		scrollingSpeed: 900,
		navigationPosition: 'right',
		continuousVertical: false,
		css3: true,
		menu: '#menu',
		autoScrolling: false,
		navigationTooltips: ['Home', 'Features', 'Categories', 'Text&Background Slider', 'Video Section', 'Contact'],
		anchors: ['home', 'features', 'categories', 'slider', 'video', 'contact'],
		scrollOverflow: true,
		afterLoad: function(anchorLink, index){
			// If Index 1
			if(index == 1){
				// Do something
			}
			// If Index 2
			if(index == 2){
				// Do something
			}
			// If AnchorLink = Categories
			if(anchorLink == 'categories'){
				// Do something
			}
			// If Index 4
			if(index == 4){
				// Do something
			}
			// If Index 5
			if(index == 5){
				// Do something
			}
			// If AnchorLink = contact
			if(anchorLink == 'contact'){
				$('#navigation-type2').addClass('active');
			} else{
				$('#navigation-type2').removeClass('active');
			}
		
		}
	});




