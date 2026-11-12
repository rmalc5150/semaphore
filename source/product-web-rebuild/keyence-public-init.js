(function (win, doc) {
    'use strict';

    var docElement = doc.documentElement;

    if (docElement && docElement.nodeType === 1) {
        docElement.setAttribute('data-script-enabled', 'true');
    }

    docElement = null;
}(window, window.document));
