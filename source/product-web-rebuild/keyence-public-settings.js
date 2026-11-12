/**
 * $Rev: 1089 $
 */

var kpi_siteSettings = {
    siteId: 1,
    siteLang: 'en-US'
};

var suz_LanguagePath = "";

/* == start Allowed only change in this area ==========================================================================*/
var kpi_usersettings = {

		SmoothScrollSpd:800/* Initial Value of Smooth Scroll Speed */

		,BacisCarouselMvSpd:600/* Initial Value of Basic Carousel Moving Speed */

		,InnerContentsCarouselMvSpd:800/* Initial Value of Frame Carousel in Contents Moving Speed */

		,FrameCarouselMvSpd:600/* Initial Value of Cross Type Navigation & Local Navigation Carousel Moving Speed */

		,CrossTypeOCSpd:600/* Initial Value of Cross Type Navigation Opening and Closing Speed */

		,CrossTypeChangeSpd:150/* Initial Value of CrossType Type Change Speed */

		,FormPullDownShowSpd:150/* Initial Value of Custom Pulldown Show Speed */

		,FormPullDownHideSpd:150/* Initial Value of Custom Pulldown Hide Speed */

		,ModalOpenSpd:300/* Initial Value of Modal Windows Open Speed */

		,SelectModelsLimitNum:10/* Initial Value of Select Models Limit Number */

		,KeyVisualSlideSpd:800/* Initial Value of Key Visual Slide Speed */

		,KeyVisualSlideStopTime:4000/* Initial Value of Key Visual Slide Stop Time */

		,KeyVisualSlideEasing:'easeInOutQuart'/* Default Easing for Key Visual Slider */

		,DeleteBtnFadeInSpd:500/* Initial Value of Delete Button Fade In Speed */

		,DeleteBtnFadeOutSpd:300/* Initial Value of Delete Button Fade Out Speed */

		/* Use Mega Menu */
		,MegaMenuRowsNum:16/* Initial Value of number of rows in columns entering by Mega Menu. */

		,MegaMenuRollOverDelay:0/* Initial Value of On Mouse Enter Global Navigation Open Delay Time */

		,MegaMenuRollOutDelay:0/* Initial Value of On Mouse Leave Global Navigation Close Delay Time */

		,MegaMenuSlideDownSpd:0/* Initial Value of Mega Menu Content Slide Down Speed */

		,MegaMenuFadeInSpd:0/* Initial Value of Mega Menu Content Fade In Speed */

		,MegaMenuFadeOutSpd:0/* Initial Value of Mega Menu Content Fade Out Speed */

		,MegaMenuSlideEasing:'easeInExpo'/* Default Easing for Mega Menu Slide Up and Down */

		/* Use Cart */
		,CartOCSpd:400/* Initial Value of Cart Slide Up and Down Speed */

		,CartItemFadeInSpd:600/* Initial Value of Cart Item Fade In Speed */

        ,CartItemFadeOutSpd:600/* Initial Value of Cart Item Fade Out Speed */

		,CartSlideEasing:'easeOutQuint'/* Default Easing for Cart Slide Up and Down */

        ,DownloadItemMaxFileSize: 52428800 /* Max File size of Download Items (50Mbyte)*/

        ,AjaxTimeoutSeconds: 5000  /* Initial Value of Ajax Timeout milli seconds */

        ,SessionKeepAliveIntervalMs: 1500000  /* Session keep-alive interval in milliseconds (25 minutes) */

		/* Top Page */
		,NewsCarouselStopTime:7/* Initial Value of News Carousel Slide Stop Time *This is the number of seconds */

		,NewsCarouselSlideSpd:1200/* Initial Value of News Carousel Slide Speed */

		,NewsCarouselEasing:'easeInExpo'/* Default Easing for News Carousel */

		/* My Keyence */
		,MoreViewNum:10/* Initial Value of Displayed Per Click More View Button */

		,ViewMoreFadeInSpd:500/* Initial Value of Related View More Fade In Speed */

		,ViewMoreFadeOutSpd:300/* Initial Value of Related View More Fade Out Speed */

		,DownloadPopupOpenDelay:2000/* Initial Value of Download Popup Open Delay */

        ,DownloadRecommendPopupOpenDelay:2000/* Initial Value of Download Recommend Popup Open Delay */

        ,RecommendPopupOpenedCountLimit:1/* Initial Value of Download Recommend Popup Opened Count Limit */

		/* Use Certified Models */
		,CertifiedModelsRowsNum:16/* Initial Value of number of rows in columns entering by Certified Models */

		/* eNews Popup */
		,enewscount:3/* Initial Value of condition pop-up opens */
		,enewslimit:182/* Initial Value of period for does not appear*/

        		/* Userlike Messenger */
        ,chatWindowDisplayDelay: 10000 /* Set the chat window display delay time in milliseconds */

};
/* == end Allowed only change in this area ==========================================================================*/


/* Need to be translate */
var kpi_translation = {
		New:"NEW"
		,Discontinued: "Discontinued"
		,ViewAllSeries:"View all series"
		,ImageLoadErrorMsg:"This image failed to load."
		,ContentLoadErrorMsg:"This content failed to load."
		,SelectRegionMsg:"Choose A Region / Language"
		,CartLimitErrorMsg:'The amount reached to limit. Please press &quot;Start Downloading.&quot;'
		,ProductCategory: 'Product Category'
		,SelectUnselectedMsg: '-- Select one --'
        ,DownloadList: 'Download List'
        ,Amount: 'Items'
        ,Selected: 'Selected'
        ,SelectedTxt: 'selected'
        ,Total: 'Total'
        ,MB: 'MB'
        ,Open: 'Open'
        ,Close: 'Close'
        ,DeleteAllItem: 'Remove All'
        ,LicenseAgreement: 'License Agreement'
        ,SoftwareLicenseAgreementTitle: 'Software'
        ,CadLicenseAgreementTitle: 'CAD'
        ,ProgressToDownload: 'Start Downloading'
        ,DeleteAllItemConfirmMessage: 'Would you like to delete all items in cart?'
		,ServerConnectErrorMessage: 'We are sorry. An unexpected error has occured.'
		,RefineSearchOpen: 'Narrow Results'
		,RefineSearchClose: 'Hide Search Criteria'
		,DescriptionLabel: 'Description'
		,OSLabel: '[OS]'
		,VersionLabel: '[Version]'
		,LastUpdateDateLabel: '[Last Updated]'
		,MyKeyenceEnqPopupHeading: 'Thank you for your download. Have any further questions?'
};


/** file type id setting **/
var kpi_fileTypeSettings = {
    '2D-DXF': 29,
    '2D-MICROCADAM': 30,
    '3D-IGES': 31,
    '3D-STEP': 32,
    '3D-Parasolid': 33,
    '3D-Acis': 34,
    '3D-SolidWorks': 35,
    '3D-CATIA': 36,
    '3D-INVENTOR': 37,
    'EPLAN': 69
};

/** language id setting **/
var kpi_languageSettings = {
    siteLang: ['en-US'],
    manualLang: ['en-GB','en-US'],
    lang: {
        'es-MX': 'Spanish',
        'zh-TW': 'Traditional Chinese',
        'zh-CN': 'Simplified Chinese',
        'ja-JP': 'Japanese',
        'de-DE': 'German',
        'fr-FR': 'French',
        'it-IT': 'Italian',
        'ko-KR': 'Korean',
        'pt-BR': 'Portuguese',
        'th-TH': 'Thai',
        'cs-CZ': 'Czech',
        'nl-NL': 'Dutch',
        'hu-HU': 'Hungarian',
        'pl-PL': 'Polish',
        'ru-RU': 'Russian',
        'sk-SK': 'Slovakian',
        'id-ID': 'Indonesian',
        'vi-VN': 'Vietnamese',
        'ro-RO': 'Romanian',
        'sl-SI': 'Slovenian',
        'en-US': 'English (US)',
        'en-GB': 'English'
    },
    lang1: {
        'es-MX': 'Spanish',
        'zh-TW': 'Traditional Chinese',
        'zh-CN': 'Simplified Chinese',
        'ja-JP': 'Japanese',
        'de-DE': 'German',
        other: 'Others'
    },
    lang2: {
        'fr-FR': 'French',
        'it-IT': 'Italian',
        'ko-KR': 'Korean',
        'pt-BR': 'Portuguese',
        'th-TH': 'Thai',
        'cs-CZ': 'Czech',
        'nl-NL': 'Dutch',
        'hu-HU': 'Hungarian',
        'pl-PL': 'Polish',
        'ru-RU': 'Russian',
        'sk-SK': 'Slovakian',
        'id-ID': 'Indonesian',
        'vi-VN': 'Vietnamese',
        'ro-RO': 'Romanian',
        'sl-SI': 'Slovenian',
	'en-US': 'English (US)',
        'en-GB': 'English'
    }
};

/* Loading Files
-------------------------------------------------------- */
var kpi_loadingfiles = {
	RegionSelectHtml:suz_LanguagePath+"/modal/region-language-selector/"
	,PrintCss:"/css/common/print.css"
	,GroupTypeListJson:"/data/group_type_list.json"
	,GroupTypeListJsonV2:"/data/group-type-list.json"
	,AboutUsHtml:suz_LanguagePath+"/data/megamenu-about-us.html"
	,ProductsHtml:suz_LanguagePath+"/data/megamenu-products.html"
	,SolutionHtml:suz_LanguagePath+"/data/megamenu-solutions.html"
	,DownloadsHtml:suz_LanguagePath+"/data/megamenu-downloads.html"
	,SupportHtml:suz_LanguagePath+"/data/megamenu-support.html"
	,IndustryApplication:"/data/industry_application_products.json"
	,RollArea:"/data/rollarea.json"
	,enewshtml:"/modal/news-events/newsletters/subscribe/enews-subscribe.jsp"
};

var kpi_cartsettings = {
    thumbnailPath: "/img/asset/"
    ,cartApiUrl:""    /* value unchangeable.  */
    ,cartApiMethodAddCart:"/ajax/cart/addCart/"
    ,cartApiMethodRemoveCart:"/ajax/cart/removeCart/"
    ,cartApiMethodRemoveAllCart:"/ajax/cart/removeAllCart/"
    ,cartApiMethodAllAssetInfo:"/ajax/cart/allAssetInfo/"
    ,cartApiMethodServerErrorMsg:"/ajax/cart/serverErrorMsg/"
    ,downloadLicenseSoft:suz_LanguagePath+"/modal/downloads/license-agree/software/"
    ,downloadLicenseCad:suz_LanguagePath+"/modal/downloads/license-agree/cad/"
    ,downloadUrl:"/download/downloadCart/"
};

var kpi_downloadListSettings = {
    listApiUrl:""
    ,listApiMethodRemoveList:"/ajax/downloadList/removeDownloadList/"
};

/* external files domain
 -------------------------------------------------------- */
var kpi_currentDomain = "";/* value unchangeable.  */

var kpi_cookiesettings = {
    cookieDomain: ".keyence.com"
    ,cookieNameDownloadAgreement:"download_agreement"
    ,cookieNameCartMode:"cart_mode"
    ,cookieNameHasAddToList:"has_addToList"
};

/** loading files For crossdomain(search site) */
var kpi_mf_modalsettings = {
    downloadLicenseSoftHtml:""
    ,downloadLicenseCadHtml:""
    ,RegionSelectHtml:""
    ,AboutUsHtml:""
    ,ProductsHtml:""
    ,SolutionHtml:""
    ,DownloadsHtml:""
    ,SupportHtml:""
}

/** domain setting. */
var kpi_originalDomain = "https://www.keyence.com";

/** enews popup setting **/
var suz_enews_settings = {
     enewsApiMethodSignUp:"/ajax/popup/index"
    ,enewsApiMethodOptIn:"/ajax/popup/soptionid"
}

/** search Domain and FilePath setting **/
var suz_search_Path = {
     searchDomainRegExp :new RegExp("www-search|china-search")
    ,topPageDecision    :["index","index.jsp"]
    ,is_subLangPath     : function(path) {
        var result = true;
        switch (path){
            case "en":
            case "jajp":
            case "engb":
            case "enus":
            case "zhcn":
            case "zhtw":
            case "dede":
            case "frfr":
            case "itit":
            case "thth":
            case "eses":
            case "esmx":
            case "cscz":
            case "nlnl":
            case "huhu":
            case "kokr":
            case "plpl":
            case "ptbr":
            case "ruru":
            case "sksk":
            case "idid":
            case "vivn":
            case "msmy":
            case "roro":
            case "slsi":
                break;
            default:
                result = false;
                break;
        }
        return result;
    }
}

var kpi_debug = false;

/**
 * This settings is changed by JavaScript from scripts.js or modalscripts.js.
 * @type {{originalDomain: string, searchDomain: string}}
 */
var kpi_domainSettings = {
	originalDomain:""
	,searchDomain:""
	,isDomain:true
};

var mfsettings = {
	"us_enus": {
		"defaultKeyword": "What are you looking for?",
		"seriesText": "Series",
		"modelsText": "Models",
		"defaultSeries": "Show models which match your keywords",
		"discontinuedText": "DISCONTINUED"
	}
};

/**
 * domain setting
 */
var kpi_protocol = location.protocol;
var kpi_host = location.host;

kpi_domainSettings.originalDomain = kpi_protocol + "//" + kpi_host + suz_LanguagePath;

if(0 <= kpi_host.search(suz_search_Path.searchDomainRegExp)) {
	kpi_domainSettings.originalDomain = kpi_protocol + kpi_originalDomain.replace(/^http+s?:/,"");

	kpi_domainSettings.isDomain = false;
	//modal settings For www-search,
	kpi_cartsettings.downloadLicenseCad = kpi_mf_modalsettings.downloadLicenseCadHtml;
	kpi_cartsettings.downloadLicenseSoft = kpi_mf_modalsettings.downloadLicenseSoftHtml;
	kpi_loadingfiles.RegionSelectHtml = kpi_mf_modalsettings.RegionSelectHtml;
	kpi_loadingfiles.AboutUsHtml = kpi_mf_modalsettings.AboutUsHtml;
	kpi_loadingfiles.ProductsHtml = kpi_mf_modalsettings.ProductsHtml;
	kpi_loadingfiles.SolutionHtml = kpi_mf_modalsettings.SolutionHtml;
	kpi_loadingfiles.DownloadsHtml = kpi_mf_modalsettings.DownloadsHtml;
	kpi_loadingfiles.SupportHtml = kpi_mf_modalsettings.SupportHtml;
}

//override
kpi_cartsettings.cartApiUrl = kpi_domainSettings.originalDomain;
kpi_downloadListSettings.listApiUrl = kpi_domainSettings.originalDomain;
kpi_currentDomain = kpi_domainSettings.originalDomain;

/** enquete session keep alive */
var suz_enquete_session = 1200000; // 20min

/** Cookie Alert Text */
var kpi_cookie_alert = {
    flag: false,
    text: '',
    btnText: '',
    privacyText: '',
    link: ''
};

/** Career Site Suggest */
var kpi_career_site_suggest = {
    text: 'KEYENCE America - Careers<br><br>You might be visiting other country\'s site.<br>Would you like to select the site for your country?',
    btnText01: 'Continue',
    btnText02: 'Select Site',
    limit: 3
};

/** Repair Page Suggest */
var kpi_repair_page_suggest = {
    text: 'KEYENCE America - Repair Service Request<br><br>You might be visiting other country\'s site.<br>Would you like to select the site for your country?',
    btnText01: 'Continue',
    btnText02: 'Select Site',
    limit: 3,
    title: 'KEYENCE America - Repair Service Request',
    leadText: 'You might be visiting other country\'s site. Would you like to select the site for your country?'
};

/** Menu Conversion */
var kpi_menu_conversion = {
    isShow: true,
    excludedUrl: new RegExp('(^(' + window.suz_LanguagePath + ')?\/ss\/)|(^(' + window.suz_LanguagePath + ')?\/landing\/(?!(lpc\/)))|(\/index_pr\.jsp$)|(^(' + window.suz_LanguagePath + ')?\/products\/.+\/.+\/.+\/(campaign|lp|pr|survey|video)\/)'),
    openDelay: 3000,
    isTelShow: true
};

/** Signin Form password error limit */
var passwordErrorCountMax = 2;

/** Search API */
var kpi_search_api = {
    version: 2,
    pathnames: {
        PAGE: '/ajax/search/v2/content/',
        ASSET: '/ajax/search/v2/asset/',
        PRODUCT: '/ajax/search/v2/product/',
        DATA_SHEET: '/ajax/search/v2/datasheet/',
        SUGGEST_SERIES: '/ajax/suggest/v2/product_series/',
        SUGGEST_MODEL: '/ajax/suggest/v2/product_model/',
        SUGGEST_PAGE: '/ajax/suggest/v2/keyword/',
        SUGGEST_ASSET: '/ajax/suggest/v2/asset/',
        PRODUCT_COMPLETE_MATCH: '/ajax/search/v2/perfect_match_product/',
        DID_YOU_MEAN_MODEL: '/ajax/didyoumean/v2/product_model/'
    }
}
