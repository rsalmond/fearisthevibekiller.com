jQuery(document).ready(function() {

/* ==============================================
FULLSCREEN HOME PAGE
============================================== */

      jQuery('.revslider').show().revolution(
      {
            dottedOverlay:"none",
            delay:16000,
            startwidth:1170,
            startheight:700,
            hideThumbs:200,
            
            thumbWidth:100,
            thumbHeight:50,
            thumbAmount:5,
            
            navigationType:"bullet",
            navigationArrows:"solo",
            navigationStyle:"preview4",
            
            touchenabled:"on",
            onHoverStop:"on",
            
            swipe_velocity: 0.7,
            swipe_min_touches: 1,
            swipe_max_touches: 1,
            drag_block_vertical: false,
                                                
            parallax:"scroll",
            parallaxBgFreeze:"on",
            parallaxDisableOnMobile:"on",
            parallaxLevels:[5,10,15,20,25,30,35,40,45,50],
                                                
            keyboardNavigation:"off",
            
            navigationHAlign:"center",
            navigationVAlign:"bottom",
            navigationHOffset:0,
            navigationVOffset:20,

            soloArrowLeftHalign:"left",
            soloArrowLeftValign:"center",
            soloArrowLeftHOffset:20,
            soloArrowLeftVOffset:0,

            soloArrowRightHalign:"right",
            soloArrowRightValign:"center",
            soloArrowRightHOffset:20,
            soloArrowRightVOffset:0,
                        
            shadow:0,
            fullWidth:"off",
            fullScreen:"on",

            spinner:"spinner4",
            
            stopLoop:"off",
            stopAfterLoops:-1,
            stopAtSlide:-1,

            shuffle:"off",
            
            autoHeight:"off",                               
            forceFullWidth:"off",                                 
                                                
            hideTimerBar: "on",               
                                                
            hideThumbsOnMobile:"off",
            hideNavDelayOnMobile:1500,                                  
            hideBulletsOnMobile:"off",
            hideArrowsOnMobile:"off",
            hideThumbsUnderResolution:0,
            
            hideSliderAtLimit:0,
            hideCaptionAtLimit:0,
            hideAllCaptionAtLilmit:0,
            startWithSlide:0,
            fullScreenOffsetContainer: ""      
      });
      
/* ==============================================
STANDART HOME PAGE (NO FULLSCREEN)
============================================== */
                                                  
      jQuery('.revslider-standart').show().revolution(
      {
            dottedOverlay:"none",
            delay:16000,
            startwidth:1170,
            startheight:700,
            hideThumbs:200,
            
            thumbWidth:100,
            thumbHeight:50,
            thumbAmount:5,
            
            navigationType:"bullet",
            navigationArrows:"solo",
            navigationStyle:"preview4",
            
            touchenabled:"on",
            onHoverStop:"on",
            
            swipe_velocity: 0.7,
            swipe_min_touches: 1,
            swipe_max_touches: 1,
            drag_block_vertical: false,
                                                
            parallax:"scroll",
            parallaxBgFreeze:"on",
            parallaxDisableOnMobile:"on",
            parallaxLevels:[5,10,15,20,25,30,35,40,45,50],
                                                
            keyboardNavigation:"off",
            
            navigationHAlign:"center",
            navigationVAlign:"bottom",
            navigationHOffset:0,
            navigationVOffset:20,

            soloArrowLeftHalign:"left",
            soloArrowLeftValign:"center",
            soloArrowLeftHOffset:20,
            soloArrowLeftVOffset:0,

            soloArrowRightHalign:"right",
            soloArrowRightValign:"center",
            soloArrowRightHOffset:20,
            soloArrowRightVOffset:0,
                        
            shadow:0,
            fullWidth:"on",
            fullScreen:"off",

            spinner:"spinner4",
            
            stopLoop:"off",
            stopAfterLoops:-1,
            stopAtSlide:-1,

            shuffle:"off",
            
            autoHeight:"off",                               
            forceFullWidth:"on",                                 
                                                
            hideTimerBar: "on",               
                                                
            hideThumbsOnMobile:"off",
            hideNavDelayOnMobile:1500,                                  
            hideBulletsOnMobile:"off",
            hideArrowsOnMobile:"off",
            hideThumbsUnderResolution:0,
            
            hideSliderAtLimit:0,
            hideCaptionAtLimit:0,
            hideAllCaptionAtLilmit:0,
            startWithSlide:0,
            fullScreenOffsetContainer: ""      
      });

/* ==============================================
STANDART HOME PAGE TYPE-BIG (NO FULLSCREEN)
============================================== */
                                                  
      jQuery('.revslider-standart-big').show().revolution(
      {
            dottedOverlay:"none",
            delay:16000,
            startwidth:1170,
            startheight:900,
            hideThumbs:200,
            
            thumbWidth:100,
            thumbHeight:50,
            thumbAmount:5,
            
            navigationType:"bullet",
            navigationArrows:"solo",
            navigationStyle:"preview4",
            
            touchenabled:"on",
            onHoverStop:"on",
            
            swipe_velocity: 0.7,
            swipe_min_touches: 1,
            swipe_max_touches: 1,
            drag_block_vertical: false,
                                                
            parallax:"scroll",
            parallaxBgFreeze:"on",
            parallaxDisableOnMobile:"on",
            parallaxLevels:[5,10,15,20,25,30,35,40,45,50],
                                                
            keyboardNavigation:"off",
            
            navigationHAlign:"center",
            navigationVAlign:"bottom",
            navigationHOffset:0,
            navigationVOffset:20,

            soloArrowLeftHalign:"left",
            soloArrowLeftValign:"center",
            soloArrowLeftHOffset:20,
            soloArrowLeftVOffset:0,

            soloArrowRightHalign:"right",
            soloArrowRightValign:"center",
            soloArrowRightHOffset:20,
            soloArrowRightVOffset:0,
                        
            shadow:0,
            fullWidth:"on",
            fullScreen:"off",

            spinner:"spinner4",
            
            stopLoop:"off",
            stopAfterLoops:-1,
            stopAtSlide:-1,

            shuffle:"off",
            
            autoHeight:"off",                               
            forceFullWidth:"on",                                 
                                                
            hideTimerBar: "on",               
                                                
            hideThumbsOnMobile:"off",
            hideNavDelayOnMobile:1500,                                  
            hideBulletsOnMobile:"off",
            hideArrowsOnMobile:"off",
            hideThumbsUnderResolution:0,
            
            hideSliderAtLimit:0,
            hideCaptionAtLimit:0,
            hideAllCaptionAtLilmit:0,
            startWithSlide:0,
            fullScreenOffsetContainer: ""      
      });

/* ==============================================
STANDART HOME PAGE TYPE-SMALL (NO FULLSCREEN)
============================================== */
                                                  
      jQuery('.revslider-standart-small').show().revolution(
      {
            dottedOverlay:"none",
            delay:16000,
            startwidth:1170,
            startheight:600,
            hideThumbs:200,
            
            thumbWidth:100,
            thumbHeight:50,
            thumbAmount:5,
            
            navigationType:"bullet",
            navigationArrows:"solo",
            navigationStyle:"preview4",
            
            touchenabled:"on",
            onHoverStop:"on",
            
            swipe_velocity: 0.7,
            swipe_min_touches: 1,
            swipe_max_touches: 1,
            drag_block_vertical: false,
                                                
            parallax:"scroll",
            parallaxBgFreeze:"on",
            parallaxDisableOnMobile:"on",
            parallaxLevels:[5,10,15,20,25,30,35,40,45,50],
                                                
            keyboardNavigation:"off",
            
            navigationHAlign:"center",
            navigationVAlign:"bottom",
            navigationHOffset:0,
            navigationVOffset:20,

            soloArrowLeftHalign:"left",
            soloArrowLeftValign:"center",
            soloArrowLeftHOffset:20,
            soloArrowLeftVOffset:0,

            soloArrowRightHalign:"right",
            soloArrowRightValign:"center",
            soloArrowRightHOffset:20,
            soloArrowRightVOffset:0,
                        
            shadow:0,
            fullWidth:"on",
            fullScreen:"off",

            spinner:"spinner4",
            
            stopLoop:"off",
            stopAfterLoops:-1,
            stopAtSlide:-1,

            shuffle:"off",
            
            autoHeight:"off",                               
            forceFullWidth:"on",                                 
                                                
            hideTimerBar: "on",               
                                                
            hideThumbsOnMobile:"off",
            hideNavDelayOnMobile:1500,                                  
            hideBulletsOnMobile:"off",
            hideArrowsOnMobile:"off",
            hideThumbsUnderResolution:0,
            
            hideSliderAtLimit:0,
            hideCaptionAtLimit:0,
            hideAllCaptionAtLilmit:0,
            startWithSlide:0,
            fullScreenOffsetContainer: ""      
      });

/* ==============================================
CONTENT SLIDER
============================================== */
                                                          
      jQuery('.content-slider').show().revolution({
            dottedOverlay:"none",
            delay:16000,
            startwidth:1170,
            startheight:600,
            hideThumbs:200,

            thumbWidth:100,
            thumbHeight:50,
            thumbAmount:4,

            navigationType:"bullet",
            navigationArrows:"solo",
            navigationStyle:"preview4",

            touchenabled:"on",
            onHoverStop:"on",

            swipe_velocity: 0.7,
            swipe_min_touches: 1,
            swipe_max_touches: 1,
            drag_block_vertical: false,
                                                
            parallax:"scroll",
            parallaxBgFreeze:"on",
            parallaxDisableOnMobile:"on",
            parallaxLevels:[5,10,15,20,25,30,35,40,45,50],
                                                
            keyboardNavigation:"off",

            navigationHAlign:"center",
            navigationVAlign:"bottom",
            navigationHOffset:0,
            navigationVOffset:20,

            soloArrowLeftHalign:"left",
            soloArrowLeftValign:"center",
            soloArrowLeftHOffset:20,
            soloArrowLeftVOffset:0,

            soloArrowRightHalign:"right",
            soloArrowRightValign:"center",
            soloArrowRightHOffset:20,
            soloArrowRightVOffset:0,

             hideTimerBar: "on",
                        
            shadow:0,
            fullWidth:"on",
            fullScreen:"off",

            spinner:"spinner4",

            stopLoop:"off",
            stopAfterLoops:-1,
            stopAtSlide:-1,

            shuffle:"off",

            autoHeight:"off",                               
            forceFullWidth:"on",                                  

            hideThumbsOnMobile:"off",
            hideNavDelayOnMobile:1500,                                  
            hideBulletsOnMobile:"off",
            hideArrowsOnMobile:"off",
            hideThumbsUnderResolution:0,

            hideSliderAtLimit:0,
            hideCaptionAtLimit:0,
            hideAllCaptionAtLilmit:0,
            startWithSlide:0  
      });

/* ==============================================
FEATURED WORKS
============================================== */

      jQuery('.featured-slider').show().revolution({

            dottedOverlay:"none",
            delay:16000,
            startwidth:960,
            startheight:430,
            hideThumbs:0,

            thumbWidth:194,
            thumbHeight:137,
            thumbAmount:10,

            navigationType:"thumb",
            navigationArrows:"solo",
            navigationStyle:"verticalcentered",
            navigationShow: "always",

            touchenabled:"on",
            onHoverStop:"on",

            swipe_velocity: 0.7,
            swipe_min_touches: 1,
            swipe_max_touches: 1,
            drag_block_vertical: false,

            parallax:"scroll",
            parallaxBgFreeze:"on",
            parallaxDisableOnMobile:"on",
            parallaxLevels:[7,4,3,2,5,4,3,2,1,0],

            keyboardNavigation:"off",

            navigationHAlign:"center",
            navigationVAlign:"bottom",
            navigationHOffset:0,
            navigationVOffset:-212,

            soloArrowLeftHalign:"left",
            soloArrowLeftValign:"center",
            soloArrowLeftHOffset:0,
            soloArrowLeftVOffset:0,

            soloArrowRightHalign:"right",
            soloArrowRightValign:"center",
            soloArrowRightHOffset:0,
            soloArrowRightVOffset:0,

            shadow:0,
            fullWidth:"off",
            fullScreen:"off",

            spinner:"spinner2",

            stopLoop:"off",
            stopAfterLoops:-1,
            stopAtSlide:-1,

            shuffle:"off",

            autoHeight:"off",
            forceFullWidth:"off",

            hideTimerBar: "on",

            hideThumbsOnMobile:"off",
            hideNavDelayOnMobile:1500,
            hideBulletsOnMobile:"off",
            hideArrowsOnMobile:"off",
            hideThumbsUnderResolution:0,

            hideSliderAtLimit:0,
            hideCaptionAtLimit:0,
            hideAllCaptionAtLilmit:0,
            startWithSlide:0,
            videoJsPath:"rs-plugin/videojs/",
            fullScreenOffsetContainer: ""

      });
                              
});   //ready

