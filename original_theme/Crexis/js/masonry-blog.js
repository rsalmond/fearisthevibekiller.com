
(function($, window, document, undefined) {
    'use strict';

/* ==============================================
MASONRY BLOG 6 COLUMNS
=============================================== */

    // init cubeportfolio
    $('#blog.masonry-blog.bl-6-col #blog-items').cubeportfolio({
        filters: '#blog.masonry-blog.bl-6-col #blog-filters',
        loadMoreAction: 'auto',
        loadMore: '#loadMore-container',
        defaultFilter: '*',
        animationType: 'scaleSides',
        gapHorizontal: 15,
        gapVertical: 15,
        gridAdjustment: 'responsive',
        mediaQueries: [{
            width: 1100,
            cols: 6
        }, {
            width: 800,
            cols: 3
        }, {
            width: 500,
            cols: 2
        }, {
            width: 320,
            cols: 1
        }],
        caption: 'zoom',
        displayType: 'lazyLoading',
        displayTypeSpeed: 100,

        // lightbox
        lightboxDelegate: '.cbp-lightbox',
        lightboxGallery: true,
        lightboxTitleSrc: 'data-title',
        lightboxCounter: '<div class="cbp-popup-lightbox-counter">{{current}} of {{total}}</div>'
    });


/* ==============================================
MASONRY BLOG - 5 COLUMNS
=============================================== */

    // init cubeportfolio
    $('#blog.masonry-blog.bl-5-col #blog-items').cubeportfolio({
        filters: '#blog.masonry-blog.bl-5-col #blog-filters',
        loadMoreAction: 'auto',
        loadMore: '#loadMore-container',
        layoutMode: 'grid',
        defaultFilter: '*',
        animationType: 'scaleSides',
        gapHorizontal: 15,
        gapVertical: 15,
        gridAdjustment: 'responsive',
        mediaQueries: [{
            width: 1100,
            cols: 5
        }, {
            width: 800,
            cols: 3
        }, {
            width: 500,
            cols: 2
        }, {
            width: 320,
            cols: 1
        }],
        caption: 'zoom',
        displayType: 'lazyLoading',
        displayTypeSpeed: 100,

        // lightbox
        lightboxDelegate: '.cbp-lightbox',
        lightboxGallery: true,
        lightboxTitleSrc: 'data-title',
        lightboxCounter: '<div class="cbp-popup-lightbox-counter">{{current}} of {{total}}</div>'
    });


/* ==============================================
MASONRY BLOG - 4 COLUMNS
=============================================== */

    // init cubeportfolio
    $('#blog.masonry-blog.bl-4-col #blog-items').cubeportfolio({
        filters: '#blog.masonry-blog.bl-4-col #blog-filters',
        loadMoreAction: 'auto',
        loadMore: '#loadMore-container',
        layoutMode: 'grid',
        defaultFilter: '*',
        animationType: 'scaleSides',
        gapHorizontal: 15,
        gapVertical: 15,
        gridAdjustment: 'responsive',
        mediaQueries: [{
            width: 1100,
            cols: 4
        }, {
            width: 800,
            cols: 3
        }, {
            width: 500,
            cols: 2
        }, {
            width: 320,
            cols: 1
        }],
        caption: 'zoom',
        displayType: 'lazyLoading',
        displayTypeSpeed: 100,

        // lightbox
        lightboxDelegate: '.cbp-lightbox',
        lightboxGallery: true,
        lightboxTitleSrc: 'data-title',
        lightboxCounter: '<div class="cbp-popup-lightbox-counter">{{current}} of {{total}}</div>'
    });



/* ==============================================
MASONRY BLOG - 3 COLUMNS
=============================================== */

    // init cubeportfolio
    $('#blog.masonry-blog.bl-3-col #blog-items').cubeportfolio({
        filters: '#blog.masonry-blog.bl-3-col #blog-filters',
        loadMoreAction: 'auto',
        loadMore: '#loadMore-container',
        layoutMode: 'grid',
        defaultFilter: '*',
        animationType: 'scaleSides',
        gapHorizontal: 15,
        gapVertical: 15,
        gridAdjustment: 'responsive',
        mediaQueries: [{
            width: 1100,
            cols: 3
        }, {
            width: 800,
            cols: 3
        }, {
            width: 500,
            cols: 2
        }, {
            width: 320,
            cols: 1
        }],
        caption: 'zoom',
        displayType: 'lazyLoading',
        displayTypeSpeed: 100,

        // lightbox
        lightboxDelegate: '.cbp-lightbox',
        lightboxGallery: true,
        lightboxTitleSrc: 'data-title',
        lightboxCounter: '<div class="cbp-popup-lightbox-counter">{{current}} of {{total}}</div>'
    });



/* ==============================================
MASONRY BLOG - 2 COLUMNS
=============================================== */

    // init cubeportfolio
    $('#blog.masonry-blog.bl-2-col #blog-items').cubeportfolio({
        filters: '#blog.masonry-blog.bl-2-col #blog-filters',
        loadMoreAction: 'auto',
        loadMore: '#loadMore-container',
        layoutMode: 'grid',
        defaultFilter: '*',
        animationType: 'scaleSides',
        gapHorizontal: 15,
        gapVertical: 15,
        gridAdjustment: 'responsive',
        mediaQueries: [{
            width: 1100,
            cols: 2
        }, {
            width: 800,
            cols: 2
        }, {
            width: 500,
            cols: 1
        }, {
            width: 320,
            cols: 1
        }],
        caption: 'zoom',
        displayType: 'lazyLoading',
        displayTypeSpeed: 100,

        // lightbox
        lightboxDelegate: '.cbp-lightbox',
        lightboxGallery: true,
        lightboxTitleSrc: 'data-title',
        lightboxCounter: '<div class="cbp-popup-lightbox-counter">{{current}} of {{total}}</div>'
    });


//End Function
})(jQuery, window, document);

