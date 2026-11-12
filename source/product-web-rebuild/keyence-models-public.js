((win, doc) => {
    'use strict';

    const MODELS_DATA = {
        TITLE: 'namePlusAlias',
        DESCRIPTION: 'salesProductName',
        OVERVIEW_LINK: 'overviewUrl',
        DISCONTINUED: 'discontinuedFlag',
        THUMBNAIL: 'thumbnail',
        DIALOG_LINK: 'dimensionsUrl',
        DATA_SHEET_LINK: 'dataSheetUrl',
        DATA_CAD_LINK: 'cadUrl',
        MANUALS_LINK: 'manualsUrl'
    };

    const GLOBAL_SETTINGS = {
        SITE_ID: win.kpi_siteSettings.siteId ? win.kpi_siteSettings.siteId : null,
        SITE_LANG: win.kpi_siteSettings.siteLang ? win.kpi_siteSettings.siteLang : null,
        ORIGINAL_DOMAIN: win.kpi_originalDomain ? win.kpi_originalDomain : null
    };

    const SETTINGS_ID = {
        GROUP: win.kpi_currentGroupId ? win.kpi_currentGroupId : null,
        TYPE: win.kpi_currentTypeId ? win.kpi_currentTypeId : null,
        SERIES: win.kpi_currentSeriesId ? win.kpi_currentSeriesId : null
    };

    const API_PATH = {
        MODELS: `${GLOBAL_SETTINGS.ORIGINAL_DOMAIN}/data/api/seriesModels?`
    };

    const PREFIX = {
        COOKIE: encodeURIComponent(GLOBAL_SETTINGS.ORIGINAL_DOMAIN.split('www.keyence.')[1])
    };

    const CONFIG = {
        SITE_API_PARAM: 'siteID',
        LANGUAGE_API_PARAM: 'languageID',
        GROUP_API_PARAM: 'groupID',
        TYPE_API_PARAM: 'typeID',
        SERIES_API_PARAM: 'seriesID',
        CATEGORY_PARAM: 'productTypeID',
        SELECT_CATEGORY_COOKIE_NAME: `kpi_has_selectCategory_${PREFIX.COOKIE}_modelTypes`
    };

    class Utility {
        static getTextOnly(textItem) {
            return textItem.replace(/(<([^>]+)>)/gi, '');
        }

        static getParam(paramName) {
            const url = new URLSearchParams(win.location.search);

            return url.get(paramName);
        }

        static getCheckedData(items) {
            const selectedDataArray = [];

            items.forEach((item) => {
                selectedDataArray.push(item.value);
            });

            return selectedDataArray;
        }

        static getJoinedArray(arrayItem) {
            if (!Array.isArray(arrayItem) || !arrayItem.length) {
                return '';
            }

            return arrayItem.join(',');
        }

        static setCookie(cookieName, cookieValue) {
            const date = new Date();
            let path;

            if (win.suz_LanguagePath) {
                path = `${win.suz_LanguagePath}/`;
            } else {
                path = '/';
            }

            date.setDate(date.getDate() + 90);
            doc.cookie = `${cookieName}=${cookieValue}; expires=${date.toUTCString()}; path=${path}`;
        }

        static getCookieValue(name) {
            const cookies = doc.cookie.split(';');

            if (!name) {
                return false;
            }

            if (!cookies.some((item) => item.trim().startsWith(`${name}=`))) {
                return false;
            }

            const targetCookie = cookies.find((item) => item.trim().startsWith(`${name}=`));

            return targetCookie.split('=')[1];
        }

        static setElementText(element, object, objectKey) {
            if (element && element.nodeType === Node.ELEMENT_NODE) {
                if (object.hasOwnProperty(objectKey) === false || !object[objectKey]) {
                    element.remove();
                } else {
                    element.textContent = Utility.getTextOnly(object[objectKey]);
                }
            }
        }

        static setElementLink(element, object, objectKey) {
            if (element && element.nodeType === Node.ELEMENT_NODE) {
                if (object.hasOwnProperty(objectKey) === false || !object[objectKey]) {
                    element.removeAttribute('href');
                } else {
                    element.href = object[objectKey];
                }
            }
        }
    }

    class SelectModelsType {
        constructor() {
            this.selectors = {
                modelsList: '.js-outputModelsData-list',
                switchItemsTarget: '.js-outputModelsData-switchItemsTarget',
                imageTarget: '.js-outputModelsData-image',
                discontinuedTarget: '.js-outputModelsData-discontinued',
                overviewLinkTarget: '.js-outputModelsData-overviewLink',
                titleTarget: '.js-outputModelsData-title',
                descriptionTarget: '.js-outputModelsData-description',
                dialogButtonTarget: '.js-outputModelsData-dialogButton',
                dialogTarget: '.js-outputModelsData-dialog',
                dataSheetLinkTarget: '.js-outputModelsData-dataSheetLink',
                cadLinkTarget: '.js-outputModelsData-cadLink',
                manualsLinkTarget: '.js-outputModelsData-manualsLink'
            };

            this.elementIdNames = {
                filterModelsTypes: 'js-filterModelsTypes',
                categoryFilterTrigger: 'js-filterModelsTypes-categoryList',
                excludeDiscontinuedNumberTarget: 'js-outputModelsData-excludeDiscontinuedNumber',
                totalNumberTarget: 'js-outputModelsData-totalNumber',
                modelsTemplate: 'js-outputModelsData-template'
            };

            this.filterModelsTypes = doc.getElementById(this.elementIdNames.filterModelsTypes);
            this.categoryFilterTrigger = doc.getElementById(this.elementIdNames.categoryFilterTrigger);
            this.excludeDiscontinuedNumberTarget = doc.getElementById(this.elementIdNames.excludeDiscontinuedNumberTarget);
            this.totalNumberTarget = doc.getElementById(this.elementIdNames.totalNumberTarget);
            this.modelsTemplate = doc.getElementById(this.elementIdNames.modelsTemplate);
            this.modelsListTarget = doc.querySelector(this.selectors.modelsList);
            this.categoryParamValue = '';
            this.cookieArray = [];
        }

        init() {
            if (!this.filterModelsTypes || !this.categoryFilterTrigger || !this.modelsListTarget || !this.modelsTemplate) {
                return;
            }

            this.allCheckBoxItem = this.filterModelsTypes.querySelector('[name="all"]');
            this.categoryCheckBoxItems = this.filterModelsTypes.querySelectorAll('[name="category"]');

            if (!this.allCheckBoxItem || !this.categoryCheckBoxItems.length) {
                return;
            }

            this.updateCookies();
            this.attachChangeEvent();
            this.getAllCategoryValue();
            this.getFilterParam();
            this.updateTriggerStatus();
            this.setSelectedData();
            this.getApiData();
            this.setMutationObserver();
        }

        updateCookies() {
            const modelTypeCookie = Utility.getCookieValue(CONFIG.SELECT_CATEGORY_COOKIE_NAME);

            if (!modelTypeCookie) {
                Utility.setCookie(CONFIG.SELECT_CATEGORY_COOKIE_NAME, JSON.stringify(this.cookieArray));
            }
        }

        attachChangeEvent() {
            this.allCheckBoxItem.addEventListener('change', this.setSelectedData.bind(this));
            this.categoryCheckBoxItems.forEach((item) => {
                item.addEventListener('change', this.setSelectedData.bind(this));
            });
        }

        getAllCategoryValue() {
            this.allCategoryIdArray = Utility.getCheckedData(this.categoryCheckBoxItems);

            if (this.allCategoryIdArray.length) {
                this.allCategoryId = Utility.getJoinedArray(this.allCategoryIdArray);
            }
        }

        getFilterParam() {
            this.categoryParamValue = Utility.getParam(CONFIG.CATEGORY_PARAM);
        }

        updateTriggerStatus() {
            if (this.categoryParamValue) {
                this.changeChecked(this.categoryParamValue);
            } else {
                const categoryCookie = Utility.getCookieValue(CONFIG.SELECT_CATEGORY_COOKIE_NAME);
                const categoryCookieArray = Utility.getJoinedArray(JSON.parse(categoryCookie));

                this.changeChecked(categoryCookieArray);
            }
        }

        changeChecked(value) {
            let checkbox = null;

            this.categoryCheckBoxItems.forEach((item) => {
                item.checked = false;
            });

            value.split(',').forEach((data) => {
                if (data === '') {
                    return;
                }

                checkbox = this.categoryFilterTrigger.querySelector(`[value="${data}"]`);

                if (checkbox) {
                    checkbox.checked = true;
                }
            });

            const allCategoryFilterTrigger = this.categoryFilterTrigger.querySelectorAll('[name="category"]:checked');

            if (this.categoryCheckBoxItems.length === allCategoryFilterTrigger.length) {
                this.allCheckBoxItem.checked = true;
            } else {
                if (!allCategoryFilterTrigger.length) {
                    this.allCheckBoxItem.checked = false;
                    this.allCheckBoxItem.indeterminate = false;
                } else {
                    this.allCheckBoxItem.checked = false;
                    this.allCheckBoxItem.indeterminate = true;
                }
            }
        }

        setSelectedData() {
            const checkedItems = this.categoryFilterTrigger.querySelectorAll('[name="category"]:checked');
            let checkedValueArray = [];
            let checkedValue = '';

            if (checkedItems.length) {
                checkedValueArray = Utility.getCheckedData(checkedItems);
                checkedValue = Utility.getJoinedArray(checkedValueArray);
                this.filterModelsTypes.dataset.selectedCategory = checkedValue;
                Utility.setCookie(CONFIG.SELECT_CATEGORY_COOKIE_NAME, JSON.stringify(checkedValueArray));
            } else {
                this.filterModelsTypes.dataset.selectedCategory = '';
                Utility.setCookie(CONFIG.SELECT_CATEGORY_COOKIE_NAME, JSON.stringify(this.cookieArray));
            }
        }

        getApiUrl() {
            const apiUrl = new URL(API_PATH.MODELS);
            const newParam = new URLSearchParams('');
            const paramCategory = Utility.getParam(CONFIG.CATEGORY_PARAM);

            newParam.set(CONFIG.SITE_API_PARAM, GLOBAL_SETTINGS.SITE_ID);
            newParam.set(CONFIG.LANGUAGE_API_PARAM, GLOBAL_SETTINGS.SITE_LANG);
            newParam.set(CONFIG.GROUP_API_PARAM, SETTINGS_ID.GROUP);
            newParam.set(CONFIG.TYPE_API_PARAM, SETTINGS_ID.TYPE);
            newParam.set(CONFIG.SERIES_API_PARAM, SETTINGS_ID.SERIES);

            if (paramCategory) {
                newParam.set(CONFIG.CATEGORY_PARAM, paramCategory);
            } else {
                const categoryCookie = Utility.getCookieValue(CONFIG.SELECT_CATEGORY_COOKIE_NAME);
                const categoryCookieArray = Utility.getJoinedArray(JSON.parse(categoryCookie));

                if (categoryCookieArray) {
                    newParam.set(CONFIG.CATEGORY_PARAM, categoryCookieArray);
                } else {
                    newParam.delete(CONFIG.CATEGORY_PARAM);
                }
            }

            this.newApiUrl = `${apiUrl}${newParam.toString()}`;

            return this.newApiUrl;
        }

        getApiData() {
            const apiUrl = this.getApiUrl();

            fetch(apiUrl).then((response) => {
                if (!response.ok) {
                    throw new Error('Network response was not OK');
                } else {
                    return response.json();
                }
            }).then((data) => {
                this.totalCount = data.totalCount ? data.totalCount : 0;
                this.count = data.count ? data.count : 0;
                this.discontinuedCount = data.discontinuedCount ? data.discontinuedCount : 0;
                this.modelsObjArray = data.models.length ? data.models : [];
                this.setProductsNumber();
                this.setModelsHtml();
            }).catch((error) => {
                console.error(error);
            });
        }

        updateDiscontinued(element) {
            this.disconCookie = Utility.getCookieValue('kpi_discon');

            if (this.disconCookie === '1') {
                element.setAttribute('aria-hidden', 'false');
            } else {
                element.setAttribute('aria-hidden', 'true');
            }
        }

        setModelsHtml() {
            const fragment = doc.createDocumentFragment();

            this.modelsListTarget.innerHTML = '';

            if (this.modelsObjArray.length === 0) {
                return;
            }

            this.modelsObjArray.forEach((modelObj) => {
                const modelsClone = this.modelsTemplate.content.cloneNode(true);

                this.modelElems = {
                    discontinued: modelsClone.querySelector(this.selectors.discontinuedTarget),
                    switchItemsTarget: modelsClone.querySelector(this.selectors.switchItemsTarget),
                    image: modelsClone.querySelector(this.selectors.imageTarget),
                    overviewLink: modelsClone.querySelector(this.selectors.overviewLinkTarget),
                    title: modelsClone.querySelector(this.selectors.titleTarget),
                    description: modelsClone.querySelector(this.selectors.descriptionTarget),
                    dialogButton: modelsClone.querySelector(this.selectors.dialogButtonTarget),
                    dialog: modelsClone.querySelector(this.selectors.dialogTarget),
                    dataSheetLink: modelsClone.querySelector(this.selectors.dataSheetLinkTarget),
                    cadLink: modelsClone.querySelector(this.selectors.cadLinkTarget),
                    manualsLink: modelsClone.querySelector(this.selectors.manualsLinkTarget)
                };

                Utility.setElementText(this.modelElems.title, modelObj, MODELS_DATA.TITLE);
                Utility.setElementText(this.modelElems.description, modelObj, MODELS_DATA.DESCRIPTION);
                Utility.setElementLink(this.modelElems.overviewLink, modelObj, MODELS_DATA.OVERVIEW_LINK);
                Utility.setElementLink(this.modelElems.dataSheetLink, modelObj, MODELS_DATA.DATA_SHEET_LINK);
                Utility.setElementLink(this.modelElems.cadLink, modelObj, MODELS_DATA.DATA_CAD_LINK);
                Utility.setElementLink(this.modelElems.manualsLink, modelObj, MODELS_DATA.MANUALS_LINK);

                if (this.modelElems.discontinued) {
                    if (modelObj.hasOwnProperty(MODELS_DATA.DISCONTINUED) === false || !modelObj[MODELS_DATA.DISCONTINUED]) {
                        this.modelElems.discontinued.remove();
                        this.modelElems.switchItemsTarget.removeAttribute('data-switch-items-target');
                    } else {
                        this.updateDiscontinued(this.modelElems.switchItemsTarget);
                    }
                }

                if (this.modelElems.image) {
                    if (modelObj.hasOwnProperty(MODELS_DATA.THUMBNAIL) === false || Object.keys(modelObj[MODELS_DATA.THUMBNAIL]).length === 0) {
                        if (!modelObj[MODELS_DATA.THUMBNAIL].url) {
                            this.modelElems.image.remove();
                        } else {
                            if (!modelObj[MODELS_DATA.THUMBNAIL].alt) {
                                this.modelElems.image.alt = '';
                            }
                        }
                    } else {
                        this.modelElems.image.src = modelObj[MODELS_DATA.THUMBNAIL].url;
                        this.modelElems.image.alt = modelObj[MODELS_DATA.THUMBNAIL].alt;
                    }
                }

                if (this.modelElems.dialogButton && this.modelElems.dialog) {
                    if (modelObj.hasOwnProperty(MODELS_DATA.DIALOG_LINK) === false || !modelObj[MODELS_DATA.DIALOG_LINK]) {
                        this.modelElems.dialogButton.disabled = true;
                        this.modelElems.dialog.remove();
                    } else {
                        this.modelElems.dialogButton.disabled = false;
                        this.modelElems.dialog.dataset.modelCardDimensionsTemplateUrlValue = modelObj[MODELS_DATA.DIALOG_LINK];
                    }
                }

                fragment.appendChild(modelsClone);
            });

            this.modelsListTarget.append(fragment);
        }

        setProductsNumber() {
            if (!this.totalNumberTarget || !this.excludeDiscontinuedNumberTarget) {
                return;
            }

            this.totalNumberTarget.textContent = this.count;
            this.excludeDiscontinuedNumberTarget.textContent = this.count - this.discontinuedCount;
        }

        setMutationObserver() {
            const observerConfig = {
                attributes: true,
                attributeOldValue: true
            };

            const callback = (record) => {
                record.forEach((data) => {
                    if (!data) {
                        return;
                    }

                    if ((data.attributeName === 'data-selected-category') &&
                        (data.oldValue !== data.target.dataset.selectedCategory)) {
                        this.updateFilterParam();
                        this.getApiData();
                    }
                });
            };

            const observer = new MutationObserver(callback.bind(this));

            observer.observe(this.filterModelsTypes, observerConfig);
        }

        updateFilterParam() {
            const urlSearchParams = new URLSearchParams(win.location.search);
            const categoryFilterDate = this.filterModelsTypes.dataset.selectedCategory;
            const baseUrl = urlSearchParams.toString();
            const urlHash = location.hash;

            if (categoryFilterDate) {
                urlSearchParams.set(CONFIG.CATEGORY_PARAM, categoryFilterDate);
            } else {
                urlSearchParams.delete(CONFIG.CATEGORY_PARAM);
            }

            if (baseUrl === urlSearchParams.toString()) {
                return;
            }

            if (urlSearchParams.toString() === '') {
                history.pushState(null, null, location.pathname + urlHash);
            } else {
                history.pushState(null, null, `?${urlSearchParams.toString()}${urlHash}`);
            }
        }
    }

    doc.addEventListener('DOMContentLoaded', () => {
        if (win.selectModelsTypeComplete === true) {
            return;
        }

        const selectModelsType = new SelectModelsType();

        selectModelsType.init();
        win.selectModelsTypeComplete = true;
    });
})(window, document);
