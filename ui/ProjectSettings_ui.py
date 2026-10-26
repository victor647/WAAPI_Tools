# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ProjectSettings.ui'
##
## Created by: Qt User Interface Compiler version 6.11.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QDialog, QDoubleSpinBox, QFormLayout, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QRadioButton, QSizePolicy,
    QSpacerItem, QSpinBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

from libraries.widgets.map_edit_widget import MapEdit

class Ui_ProjectSettings(object):
    def setupUi(self, ProjectSettingsWindow):
        if not ProjectSettingsWindow.objectName():
            ProjectSettingsWindow.setObjectName(u"ProjectSettingsWindow")
        ProjectSettingsWindow.resize(820, 640)
        self.verticalLayout = QVBoxLayout(ProjectSettingsWindow)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tabWidget = QTabWidget(ProjectSettingsWindow)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabNaming = QWidget()
        self.tabNaming.setObjectName(u"tabNaming")
        self.tabNamingLayout = QVBoxLayout(self.tabNaming)
        self.tabNamingLayout.setObjectName(u"tabNamingLayout")
        self.regulationSwitches = QGridLayout()
        self.regulationSwitches.setObjectName(u"regulationSwitches")
        self.cbxEnableAcronym = QCheckBox(self.tabNaming)
        self.cbxEnableAcronym.setObjectName(u"cbxEnableAcronym")
        self.cbxEnableAcronym.setChecked(True)

        self.regulationSwitches.addWidget(self.cbxEnableAcronym, 0, 0, 1, 1)

        self.cbxEnableColor = QCheckBox(self.tabNaming)
        self.cbxEnableColor.setObjectName(u"cbxEnableColor")
        self.cbxEnableColor.setChecked(True)

        self.regulationSwitches.addWidget(self.cbxEnableColor, 0, 1, 1, 1)

        self.cbxEnableNameCase = QCheckBox(self.tabNaming)
        self.cbxEnableNameCase.setObjectName(u"cbxEnableNameCase")
        self.cbxEnableNameCase.setChecked(True)

        self.regulationSwitches.addWidget(self.cbxEnableNameCase, 0, 2, 1, 1)

        self.cbbNameCase = QComboBox(self.tabNaming)
        self.cbbNameCase.addItem("")
        self.cbbNameCase.addItem("")
        self.cbbNameCase.addItem("")
        self.cbbNameCase.setObjectName(u"cbbNameCase")

        self.regulationSwitches.addWidget(self.cbbNameCase, 1, 2, 1, 1)

        self.cbxEnablePathLength = QCheckBox(self.tabNaming)
        self.cbxEnablePathLength.setObjectName(u"cbxEnablePathLength")
        self.cbxEnablePathLength.setChecked(True)

        self.regulationSwitches.addWidget(self.cbxEnablePathLength, 0, 3, 1, 1)

        self.cbxFullNameInSound = QCheckBox(self.tabNaming)
        self.cbxFullNameInSound.setObjectName(u"cbxFullNameInSound")

        self.regulationSwitches.addWidget(self.cbxFullNameInSound, 1, 3, 1, 1)

        self.regulationSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.regulationSwitches.addItem(self.regulationSpacer, 0, 4, 2, 1)


        self.tabNamingLayout.addLayout(self.regulationSwitches)

        self.grpBankSettings = QGroupBox(self.tabNaming)
        self.grpBankSettings.setObjectName(u"grpBankSettings")
        self.bankSettingsLayout = QHBoxLayout(self.grpBankSettings)
        self.bankSettingsLayout.setObjectName(u"bankSettingsLayout")
        self.cbxAutoDefinedBank = QCheckBox(self.grpBankSettings)
        self.cbxAutoDefinedBank.setObjectName(u"cbxAutoDefinedBank")
        self.cbxAutoDefinedBank.setChecked(True)

        self.bankSettingsLayout.addWidget(self.cbxAutoDefinedBank)

        self.cbxSplitEventMedia = QCheckBox(self.grpBankSettings)
        self.cbxSplitEventMedia.setObjectName(u"cbxSplitEventMedia")

        self.bankSettingsLayout.addWidget(self.cbxSplitEventMedia)

        self.bankSettingsSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.bankSettingsLayout.addItem(self.bankSettingsSpacer)


        self.tabNamingLayout.addWidget(self.grpBankSettings)

        self.grpEventSettings = QGroupBox(self.tabNaming)
        self.grpEventSettings.setObjectName(u"grpEventSettings")
        self.eventSettingsLayout = QHBoxLayout(self.grpEventSettings)
        self.eventSettingsLayout.setObjectName(u"eventSettingsLayout")
        self.cbxPlayPrefixInEvent = QCheckBox(self.grpEventSettings)
        self.cbxPlayPrefixInEvent.setObjectName(u"cbxPlayPrefixInEvent")

        self.eventSettingsLayout.addWidget(self.cbxPlayPrefixInEvent)

        self.cbxEventRefDarkColor = QCheckBox(self.grpEventSettings)
        self.cbxEventRefDarkColor.setObjectName(u"cbxEventRefDarkColor")
        self.cbxEventRefDarkColor.setChecked(True)

        self.eventSettingsLayout.addWidget(self.cbxEventRefDarkColor)

        self.cbxEventRefNotes = QCheckBox(self.grpEventSettings)
        self.cbxEventRefNotes.setObjectName(u"cbxEventRefNotes")
        self.cbxEventRefNotes.setChecked(True)

        self.eventSettingsLayout.addWidget(self.cbxEventRefNotes)

        self.eventSettingsSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.eventSettingsLayout.addItem(self.eventSettingsSpacer)


        self.tabNamingLayout.addWidget(self.grpEventSettings)

        self.grpLocalizationSettings = QGroupBox(self.tabNaming)
        self.grpLocalizationSettings.setObjectName(u"grpLocalizationSettings")
        self.localizationSettingsLayout = QHBoxLayout(self.grpLocalizationSettings)
        self.localizationSettingsLayout.setObjectName(u"localizationSettingsLayout")
        self.cbxLanguageInFileName = QCheckBox(self.grpLocalizationSettings)
        self.cbxLanguageInFileName.setObjectName(u"cbxLanguageInFileName")

        self.localizationSettingsLayout.addWidget(self.cbxLanguageInFileName)

        self.localizationSettingsSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.localizationSettingsLayout.addItem(self.localizationSettingsSpacer)


        self.tabNamingLayout.addWidget(self.grpLocalizationSettings)

        self.wgtNamingContent = QWidget(self.tabNaming)
        self.wgtNamingContent.setObjectName(u"wgtNamingContent")
        self.namingColumns = QHBoxLayout(self.wgtNamingContent)
        self.namingColumns.setObjectName(u"namingColumns")
        self.namingColumns.setContentsMargins(0, 0, 0, 0)
        self.categoryColumn = QVBoxLayout()
        self.categoryColumn.setObjectName(u"categoryColumn")
        self.lblCategoryHeader = QLabel(self.wgtNamingContent)
        self.lblCategoryHeader.setObjectName(u"lblCategoryHeader")

        self.categoryColumn.addWidget(self.lblCategoryHeader)

        self.categoryMap = MapEdit(self.wgtNamingContent)
        self.categoryMap.setObjectName(u"categoryMap")
        self.categoryMap.setMinimumSize(QSize(0, 200))

        self.categoryColumn.addWidget(self.categoryMap)


        self.namingColumns.addLayout(self.categoryColumn)

        self.namingRightColumn = QVBoxLayout()
        self.namingRightColumn.setObjectName(u"namingRightColumn")
        self.lblContainerHeader = QLabel(self.wgtNamingContent)
        self.lblContainerHeader.setObjectName(u"lblContainerHeader")

        self.namingRightColumn.addWidget(self.lblContainerHeader)

        self.containerSuffix = MapEdit(self.wgtNamingContent)
        self.containerSuffix.setObjectName(u"containerSuffix")
        self.containerSuffix.setMinimumSize(QSize(0, 100))
        self.containerSuffix.setMaximumSize(QSize(16777215, 140))

        self.namingRightColumn.addWidget(self.containerSuffix)

        self.netRoleGroupRow = QHBoxLayout()
        self.netRoleGroupRow.setObjectName(u"netRoleGroupRow")
        self.lblGroupHeader = QLabel(self.wgtNamingContent)
        self.lblGroupHeader.setObjectName(u"lblGroupHeader")

        self.netRoleGroupRow.addWidget(self.lblGroupHeader)

        self.iptNetRoleGroup = QLineEdit(self.wgtNamingContent)
        self.iptNetRoleGroup.setObjectName(u"iptNetRoleGroup")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.iptNetRoleGroup.sizePolicy().hasHeightForWidth())
        self.iptNetRoleGroup.setSizePolicy(sizePolicy)

        self.netRoleGroupRow.addWidget(self.iptNetRoleGroup)


        self.namingRightColumn.addLayout(self.netRoleGroupRow)

        self.netRoleValues = MapEdit(self.wgtNamingContent)
        self.netRoleValues.setObjectName(u"netRoleValues")
        self.netRoleValues.setMinimumSize(QSize(0, 140))

        self.namingRightColumn.addWidget(self.netRoleValues)

        self.namingRightSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.namingRightColumn.addItem(self.namingRightSpacer)


        self.namingColumns.addLayout(self.namingRightColumn)


        self.tabNamingLayout.addWidget(self.wgtNamingContent)

        self.tabWidget.addTab(self.tabNaming, "")
        self.tabTools = QWidget()
        self.tabTools.setObjectName(u"tabTools")
        self.tabToolsLayout = QVBoxLayout(self.tabTools)
        self.tabToolsLayout.setObjectName(u"tabToolsLayout")
        self.grpSearchAndFilter = QGroupBox(self.tabTools)
        self.grpSearchAndFilter.setObjectName(u"grpSearchAndFilter")
        self.searchAndFilterLayout = QVBoxLayout(self.grpSearchAndFilter)
        self.searchAndFilterLayout.setObjectName(u"searchAndFilterLayout")
        self.searchRow = QHBoxLayout()
        self.searchRow.setObjectName(u"searchRow")
        self.cbxAutoFetchChildren = QCheckBox(self.grpSearchAndFilter)
        self.cbxAutoFetchChildren.setObjectName(u"cbxAutoFetchChildren")

        self.searchRow.addWidget(self.cbxAutoFetchChildren)

        self.cbxFindFilterCheckedOnly = QCheckBox(self.grpSearchAndFilter)
        self.cbxFindFilterCheckedOnly.setObjectName(u"cbxFindFilterCheckedOnly")

        self.searchRow.addWidget(self.cbxFindFilterCheckedOnly)

        self.cbxKeepSelf = QCheckBox(self.grpSearchAndFilter)
        self.cbxKeepSelf.setObjectName(u"cbxKeepSelf")

        self.searchRow.addWidget(self.cbxKeepSelf)

        self.lblPageSize = QLabel(self.grpSearchAndFilter)
        self.lblPageSize.setObjectName(u"lblPageSize")

        self.searchRow.addWidget(self.lblPageSize)

        self.spbPageSize = QSpinBox(self.grpSearchAndFilter)
        self.spbPageSize.setObjectName(u"spbPageSize")
        self.spbPageSize.setMinimum(50)
        self.spbPageSize.setMaximum(5000)
        self.spbPageSize.setSingleStep(50)
        self.spbPageSize.setValue(500)

        self.searchRow.addWidget(self.spbPageSize)

        self.searchRowSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.searchRow.addItem(self.searchRowSpacer)


        self.searchAndFilterLayout.addLayout(self.searchRow)

        self.filterCheckRow = QHBoxLayout()
        self.filterCheckRow.setObjectName(u"filterCheckRow")
        self.cbxCaseSensitive = QCheckBox(self.grpSearchAndFilter)
        self.cbxCaseSensitive.setObjectName(u"cbxCaseSensitive")

        self.filterCheckRow.addWidget(self.cbxCaseSensitive)

        self.cbxOnlyIncluded = QCheckBox(self.grpSearchAndFilter)
        self.cbxOnlyIncluded.setObjectName(u"cbxOnlyIncluded")

        self.filterCheckRow.addWidget(self.cbxOnlyIncluded)

        self.cbxOnlyInUse = QCheckBox(self.grpSearchAndFilter)
        self.cbxOnlyInUse.setObjectName(u"cbxOnlyInUse")

        self.filterCheckRow.addWidget(self.cbxOnlyInUse)

        self.filterCheckSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.filterCheckRow.addItem(self.filterCheckSpacer)


        self.searchAndFilterLayout.addLayout(self.filterCheckRow)

        self.filterRadioRow = QHBoxLayout()
        self.filterRadioRow.setObjectName(u"filterRadioRow")
        self.lblEventFilter = QLabel(self.grpSearchAndFilter)
        self.lblEventFilter.setObjectName(u"lblEventFilter")

        self.filterRadioRow.addWidget(self.lblEventFilter)

        self.rbnEventAll = QRadioButton(self.grpSearchAndFilter)
        self.rbnEventAll.setObjectName(u"rbnEventAll")
        self.rbnEventAll.setChecked(True)

        self.filterRadioRow.addWidget(self.rbnEventAll)

        self.rbnEventHas = QRadioButton(self.grpSearchAndFilter)
        self.rbnEventHas.setObjectName(u"rbnEventHas")

        self.filterRadioRow.addWidget(self.rbnEventHas)

        self.rbnEventNo = QRadioButton(self.grpSearchAndFilter)
        self.rbnEventNo.setObjectName(u"rbnEventNo")

        self.filterRadioRow.addWidget(self.rbnEventNo)

        self.filterRadioMiddleSpacer = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.filterRadioRow.addItem(self.filterRadioMiddleSpacer)

        self.lblLanguageFilter = QLabel(self.grpSearchAndFilter)
        self.lblLanguageFilter.setObjectName(u"lblLanguageFilter")

        self.filterRadioRow.addWidget(self.lblLanguageFilter)

        self.rbnLangAll = QRadioButton(self.grpSearchAndFilter)
        self.rbnLangAll.setObjectName(u"rbnLangAll")
        self.rbnLangAll.setChecked(True)

        self.filterRadioRow.addWidget(self.rbnLangAll)

        self.rbnLangActive = QRadioButton(self.grpSearchAndFilter)
        self.rbnLangActive.setObjectName(u"rbnLangActive")

        self.filterRadioRow.addWidget(self.rbnLangActive)

        self.filterRadioEndSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.filterRadioRow.addItem(self.filterRadioEndSpacer)


        self.searchAndFilterLayout.addLayout(self.filterRadioRow)


        self.tabToolsLayout.addWidget(self.grpSearchAndFilter)

        self.cbxDetailLog = QCheckBox(self.tabTools)
        self.cbxDetailLog.setObjectName(u"cbxDetailLog")

        self.tabToolsLayout.addWidget(self.cbxDetailLog)

        self.cbxDumpOnlyWritable = QCheckBox(self.tabTools)
        self.cbxDumpOnlyWritable.setObjectName(u"cbxDumpOnlyWritable")

        self.tabToolsLayout.addWidget(self.cbxDumpOnlyWritable)

        self.grpConversion = QGroupBox(self.tabTools)
        self.grpConversion.setObjectName(u"grpConversion")
        self.conversionRow = QHBoxLayout(self.grpConversion)
        self.conversionRow.setObjectName(u"conversionRow")
        self.lblConversionDominance = QLabel(self.grpConversion)
        self.lblConversionDominance.setObjectName(u"lblConversionDominance")

        self.conversionRow.addWidget(self.lblConversionDominance)

        self.spbConversionDominance = QSpinBox(self.grpConversion)
        self.spbConversionDominance.setObjectName(u"spbConversionDominance")
        self.spbConversionDominance.setMinimum(50)
        self.spbConversionDominance.setMaximum(100)
        self.spbConversionDominance.setSingleStep(5)
        self.spbConversionDominance.setValue(60)

        self.conversionRow.addWidget(self.spbConversionDominance)

        self.conversionRowSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.conversionRow.addItem(self.conversionRowSpacer)


        self.tabToolsLayout.addWidget(self.grpConversion)

        self.grpLoudness = QGroupBox(self.tabTools)
        self.grpLoudness.setObjectName(u"grpLoudness")
        self.loudnessRow = QHBoxLayout(self.grpLoudness)
        self.loudnessRow.setObjectName(u"loudnessRow")
        self.lblLoudnessStandard = QLabel(self.grpLoudness)
        self.lblLoudnessStandard.setObjectName(u"lblLoudnessStandard")

        self.loudnessRow.addWidget(self.lblLoudnessStandard)

        self.cbbLoudnessStandard = QComboBox(self.grpLoudness)
        self.cbbLoudnessStandard.addItem("")
        self.cbbLoudnessStandard.addItem("")
        self.cbbLoudnessStandard.setObjectName(u"cbbLoudnessStandard")
        self.cbbLoudnessStandard.setMinimumSize(QSize(90, 0))

        self.loudnessRow.addWidget(self.cbbLoudnessStandard)

        self.lblTargetLoudness = QLabel(self.grpLoudness)
        self.lblTargetLoudness.setObjectName(u"lblTargetLoudness")

        self.loudnessRow.addWidget(self.lblTargetLoudness)

        self.spbTargetLoudness = QSpinBox(self.grpLoudness)
        self.spbTargetLoudness.setObjectName(u"spbTargetLoudness")
        self.spbTargetLoudness.setMinimum(-60)
        self.spbTargetLoudness.setMaximum(0)
        self.spbTargetLoudness.setValue(-18)

        self.loudnessRow.addWidget(self.spbTargetLoudness)

        self.lblLoudnessTolerance = QLabel(self.grpLoudness)
        self.lblLoudnessTolerance.setObjectName(u"lblLoudnessTolerance")

        self.loudnessRow.addWidget(self.lblLoudnessTolerance)

        self.spbLoudnessTolerance = QDoubleSpinBox(self.grpLoudness)
        self.spbLoudnessTolerance.setObjectName(u"spbLoudnessTolerance")
        self.spbLoudnessTolerance.setDecimals(1)
        self.spbLoudnessTolerance.setMinimum(0.000000000000000)
        self.spbLoudnessTolerance.setMaximum(20.000000000000000)
        self.spbLoudnessTolerance.setSingleStep(0.500000000000000)
        self.spbLoudnessTolerance.setValue(1.000000000000000)

        self.loudnessRow.addWidget(self.spbLoudnessTolerance)

        self.loudnessSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.loudnessRow.addItem(self.loudnessSpacer)


        self.tabToolsLayout.addWidget(self.grpLoudness)

        self.grpLocalization = QGroupBox(self.tabTools)
        self.grpLocalization.setObjectName(u"grpLocalization")
        self.localizationLayout = QVBoxLayout(self.grpLocalization)
        self.localizationLayout.setObjectName(u"localizationLayout")
        self.referenceLanguageRow = QHBoxLayout()
        self.referenceLanguageRow.setObjectName(u"referenceLanguageRow")
        self.lblReferenceLanguage = QLabel(self.grpLocalization)
        self.lblReferenceLanguage.setObjectName(u"lblReferenceLanguage")

        self.referenceLanguageRow.addWidget(self.lblReferenceLanguage)

        self.cbxUseDefaultReferenceLanguage = QCheckBox(self.grpLocalization)
        self.cbxUseDefaultReferenceLanguage.setObjectName(u"cbxUseDefaultReferenceLanguage")

        self.referenceLanguageRow.addWidget(self.cbxUseDefaultReferenceLanguage)

        self.ledReferenceLanguage = QLineEdit(self.grpLocalization)
        self.ledReferenceLanguage.setObjectName(u"ledReferenceLanguage")
        self.ledReferenceLanguage.setMinimumSize(QSize(120, 0))

        self.referenceLanguageRow.addWidget(self.ledReferenceLanguage)

        self.referenceLanguageSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.referenceLanguageRow.addItem(self.referenceLanguageSpacer)

        self.lblLanguagesHeader = QLabel(self.grpLocalization)
        self.lblLanguagesHeader.setObjectName(u"lblLanguagesHeader")

        self.referenceLanguageRow.addWidget(self.lblLanguagesHeader)

        self.iptLanguages = QLineEdit(self.grpLocalization)
        self.iptLanguages.setObjectName(u"iptLanguages")
        self.iptLanguages.setMinimumSize(QSize(220, 0))

        self.referenceLanguageRow.addWidget(self.iptLanguages)


        self.localizationLayout.addLayout(self.referenceLanguageRow)

        self.silenceDurationRow = QHBoxLayout()
        self.silenceDurationRow.setObjectName(u"silenceDurationRow")
        self.lblSilenceDuration = QLabel(self.grpLocalization)
        self.lblSilenceDuration.setObjectName(u"lblSilenceDuration")

        self.silenceDurationRow.addWidget(self.lblSilenceDuration)

        self.spbSilenceDuration = QDoubleSpinBox(self.grpLocalization)
        self.spbSilenceDuration.setObjectName(u"spbSilenceDuration")
        self.spbSilenceDuration.setDecimals(1)
        self.spbSilenceDuration.setMinimum(0.100000000000000)
        self.spbSilenceDuration.setMaximum(60.000000000000000)
        self.spbSilenceDuration.setSingleStep(0.500000000000000)
        self.spbSilenceDuration.setValue(2.000000000000000)

        self.silenceDurationRow.addWidget(self.spbSilenceDuration)

        self.silenceDurationSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.silenceDurationRow.addItem(self.silenceDurationSpacer)


        self.localizationLayout.addLayout(self.silenceDurationRow)


        self.tabToolsLayout.addWidget(self.grpLocalization)

        self.grpAudioPreview = QGroupBox(self.tabTools)
        self.grpAudioPreview.setObjectName(u"grpAudioPreview")
        self.audioPreviewLayout = QVBoxLayout(self.grpAudioPreview)
        self.audioPreviewLayout.setObjectName(u"audioPreviewLayout")
        self.previewModeRow = QHBoxLayout()
        self.previewModeRow.setObjectName(u"previewModeRow")
        self.lblPreviewDisplayMode = QLabel(self.grpAudioPreview)
        self.lblPreviewDisplayMode.setObjectName(u"lblPreviewDisplayMode")

        self.previewModeRow.addWidget(self.lblPreviewDisplayMode)

        self.cbbPreviewDisplayMode = QComboBox(self.grpAudioPreview)
        self.cbbPreviewDisplayMode.addItem("")
        self.cbbPreviewDisplayMode.addItem("")
        self.cbbPreviewDisplayMode.setObjectName(u"cbbPreviewDisplayMode")

        self.previewModeRow.addWidget(self.cbbPreviewDisplayMode)

        self.previewModeSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.previewModeRow.addItem(self.previewModeSpacer)


        self.audioPreviewLayout.addLayout(self.previewModeRow)

        self.loudnessBufferRow = QHBoxLayout()
        self.loudnessBufferRow.setObjectName(u"loudnessBufferRow")
        self.lblLoudnessBuffer = QLabel(self.grpAudioPreview)
        self.lblLoudnessBuffer.setObjectName(u"lblLoudnessBuffer")

        self.loudnessBufferRow.addWidget(self.lblLoudnessBuffer)

        self.spbLoudnessBuffer = QSpinBox(self.grpAudioPreview)
        self.spbLoudnessBuffer.setObjectName(u"spbLoudnessBuffer")
        self.spbLoudnessBuffer.setMinimum(128)
        self.spbLoudnessBuffer.setMaximum(65536)
        self.spbLoudnessBuffer.setSingleStep(128)
        self.spbLoudnessBuffer.setValue(1024)

        self.loudnessBufferRow.addWidget(self.spbLoudnessBuffer)

        self.loudnessBufferSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.loudnessBufferRow.addItem(self.loudnessBufferSpacer)


        self.audioPreviewLayout.addLayout(self.loudnessBufferRow)


        self.tabToolsLayout.addWidget(self.grpAudioPreview)

        self.grpRandomCount = QGroupBox(self.tabTools)
        self.grpRandomCount.setObjectName(u"grpRandomCount")
        self.randomCountLayout = QVBoxLayout(self.grpRandomCount)
        self.randomCountLayout.setObjectName(u"randomCountLayout")
        self.lblRandomCountHint = QLabel(self.grpRandomCount)
        self.lblRandomCountHint.setObjectName(u"lblRandomCountHint")
        self.lblRandomCountHint.setWordWrap(True)

        self.randomCountLayout.addWidget(self.lblRandomCountHint)

        self.tblRandomAllowedCounts = QTableWidget(self.grpRandomCount)
        self.tblRandomAllowedCounts.setObjectName(u"tblRandomAllowedCounts")
        self.tblRandomAllowedCounts.setMaximumSize(QSize(16777215, 80))
        self.tblRandomAllowedCounts.setMinimumSize(QSize(0, 60))
        self.tblRandomAllowedCounts.setAlternatingRowColors(True)
        self.tblRandomAllowedCounts.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tblRandomAllowedCounts.verticalHeader().setVisible(False)

        self.randomCountLayout.addWidget(self.tblRandomAllowedCounts)


        self.tabToolsLayout.addWidget(self.grpRandomCount)

        self.toolsSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.tabToolsLayout.addItem(self.toolsSpacer)

        self.tabWidget.addTab(self.tabTools, "")
        self.tabVersionControl = QWidget()
        self.tabVersionControl.setObjectName(u"tabVersionControl")
        self.tabVersionControlLayout = QVBoxLayout(self.tabVersionControl)
        self.tabVersionControlLayout.setObjectName(u"tabVersionControlLayout")
        self.vcsForm = QFormLayout()
        self.vcsForm.setObjectName(u"vcsForm")
        self.lblVcsMode = QLabel(self.tabVersionControl)
        self.lblVcsMode.setObjectName(u"lblVcsMode")

        self.vcsForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblVcsMode)

        self.cbbVcsMode = QComboBox(self.tabVersionControl)
        self.cbbVcsMode.setObjectName(u"cbbVcsMode")

        self.vcsForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.cbbVcsMode)

        self.lblP4Server = QLabel(self.tabVersionControl)
        self.lblP4Server.setObjectName(u"lblP4Server")

        self.vcsForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lblP4Server)

        self.iptP4Server = QLineEdit(self.tabVersionControl)
        self.iptP4Server.setObjectName(u"iptP4Server")

        self.vcsForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.iptP4Server)

        self.lblP4Charset = QLabel(self.tabVersionControl)
        self.lblP4Charset.setObjectName(u"lblP4Charset")

        self.vcsForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lblP4Charset)

        self.iptP4Charset = QLineEdit(self.tabVersionControl)
        self.iptP4Charset.setObjectName(u"iptP4Charset")

        self.vcsForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.iptP4Charset)

        self.lblP4ChangelistDescription = QLabel(self.tabVersionControl)
        self.lblP4ChangelistDescription.setObjectName(u"lblP4ChangelistDescription")

        self.vcsForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lblP4ChangelistDescription)

        self.iptP4ChangelistDescription = QLineEdit(self.tabVersionControl)
        self.iptP4ChangelistDescription.setObjectName(u"iptP4ChangelistDescription")

        self.vcsForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.iptP4ChangelistDescription)

        self.lblSvnExecutable = QLabel(self.tabVersionControl)
        self.lblSvnExecutable.setObjectName(u"lblSvnExecutable")

        self.vcsForm.setWidget(4, QFormLayout.ItemRole.LabelRole, self.lblSvnExecutable)

        self.iptSvnExecutable = QLineEdit(self.tabVersionControl)
        self.iptSvnExecutable.setObjectName(u"iptSvnExecutable")

        self.vcsForm.setWidget(4, QFormLayout.ItemRole.FieldRole, self.iptSvnExecutable)

        self.lblSvnUsername = QLabel(self.tabVersionControl)
        self.lblSvnUsername.setObjectName(u"lblSvnUsername")

        self.vcsForm.setWidget(5, QFormLayout.ItemRole.LabelRole, self.lblSvnUsername)

        self.iptSvnUsername = QLineEdit(self.tabVersionControl)
        self.iptSvnUsername.setObjectName(u"iptSvnUsername")

        self.vcsForm.setWidget(5, QFormLayout.ItemRole.FieldRole, self.iptSvnUsername)

        self.lblSvnPassword = QLabel(self.tabVersionControl)
        self.lblSvnPassword.setObjectName(u"lblSvnPassword")

        self.vcsForm.setWidget(6, QFormLayout.ItemRole.LabelRole, self.lblSvnPassword)

        self.iptSvnPassword = QLineEdit(self.tabVersionControl)
        self.iptSvnPassword.setObjectName(u"iptSvnPassword")
        self.iptSvnPassword.setEchoMode(QLineEdit.Password)

        self.vcsForm.setWidget(6, QFormLayout.ItemRole.FieldRole, self.iptSvnPassword)

        self.lblSvnCommitMessage = QLabel(self.tabVersionControl)
        self.lblSvnCommitMessage.setObjectName(u"lblSvnCommitMessage")

        self.vcsForm.setWidget(7, QFormLayout.ItemRole.LabelRole, self.lblSvnCommitMessage)

        self.iptSvnCommitMessage = QLineEdit(self.tabVersionControl)
        self.iptSvnCommitMessage.setObjectName(u"iptSvnCommitMessage")

        self.vcsForm.setWidget(7, QFormLayout.ItemRole.FieldRole, self.iptSvnCommitMessage)

        self.btnVcsTest = QPushButton(self.tabVersionControl)
        self.btnVcsTest.setObjectName(u"btnVcsTest")

        self.vcsForm.setWidget(8, QFormLayout.ItemRole.SpanningRole, self.btnVcsTest)


        self.tabVersionControlLayout.addLayout(self.vcsForm)

        self.vcsSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.tabVersionControlLayout.addItem(self.vcsSpacer)

        self.tabWidget.addTab(self.tabVersionControl, "")
        self.tabAi = QWidget()
        self.tabAi.setObjectName(u"tabAi")
        self.tabAiLayout = QVBoxLayout(self.tabAi)
        self.tabAiLayout.setObjectName(u"tabAiLayout")
        self.aiForm = QFormLayout()
        self.aiForm.setObjectName(u"aiForm")
        self.lblAiMode = QLabel(self.tabAi)
        self.lblAiMode.setObjectName(u"lblAiMode")

        self.aiForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblAiMode)

        self.cbbAiMode = QComboBox(self.tabAi)
        self.cbbAiMode.setObjectName(u"cbbAiMode")

        self.aiForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.cbbAiMode)

        self.lblAiProvider = QLabel(self.tabAi)
        self.lblAiProvider.setObjectName(u"lblAiProvider")

        self.aiForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lblAiProvider)

        self.cbbAiProvider = QComboBox(self.tabAi)
        self.cbbAiProvider.setObjectName(u"cbbAiProvider")

        self.aiForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.cbbAiProvider)

        self.lblAiProxy = QLabel(self.tabAi)
        self.lblAiProxy.setObjectName(u"lblAiProxy")

        self.aiForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lblAiProxy)

        self.iptAiProxy = QLineEdit(self.tabAi)
        self.iptAiProxy.setObjectName(u"iptAiProxy")

        self.aiForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.iptAiProxy)

        self.lblAiBaseUrl = QLabel(self.tabAi)
        self.lblAiBaseUrl.setObjectName(u"lblAiBaseUrl")

        self.aiForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lblAiBaseUrl)

        self.iptAiBaseUrl = QLineEdit(self.tabAi)
        self.iptAiBaseUrl.setObjectName(u"iptAiBaseUrl")

        self.aiForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.iptAiBaseUrl)

        self.lblAiApiKey = QLabel(self.tabAi)
        self.lblAiApiKey.setObjectName(u"lblAiApiKey")

        self.aiForm.setWidget(4, QFormLayout.ItemRole.LabelRole, self.lblAiApiKey)

        self.iptAiApiKey = QLineEdit(self.tabAi)
        self.iptAiApiKey.setObjectName(u"iptAiApiKey")
        self.iptAiApiKey.setEchoMode(QLineEdit.Password)

        self.aiForm.setWidget(4, QFormLayout.ItemRole.FieldRole, self.iptAiApiKey)

        self.lblAiModel = QLabel(self.tabAi)
        self.lblAiModel.setObjectName(u"lblAiModel")

        self.aiForm.setWidget(5, QFormLayout.ItemRole.LabelRole, self.lblAiModel)

        self.iptAiModel = QLineEdit(self.tabAi)
        self.iptAiModel.setObjectName(u"iptAiModel")

        self.aiForm.setWidget(5, QFormLayout.ItemRole.FieldRole, self.iptAiModel)

        self.cbxAiEnableScript = QCheckBox(self.tabAi)
        self.cbxAiEnableScript.setObjectName(u"cbxAiEnableScript")

        self.aiForm.setWidget(6, QFormLayout.ItemRole.SpanningRole, self.cbxAiEnableScript)

        self.lblAiMaxContext = QLabel(self.tabAi)
        self.lblAiMaxContext.setObjectName(u"lblAiMaxContext")

        self.aiForm.setWidget(7, QFormLayout.ItemRole.LabelRole, self.lblAiMaxContext)

        self.spnAiMaxContext = QSpinBox(self.tabAi)
        self.spnAiMaxContext.setObjectName(u"spnAiMaxContext")
        self.spnAiMaxContext.setMinimum(1)
        self.spnAiMaxContext.setMaximum(10000)
        self.spnAiMaxContext.setValue(500)

        self.aiForm.setWidget(7, QFormLayout.ItemRole.FieldRole, self.spnAiMaxContext)

        self.lblAiMaxTurns = QLabel(self.tabAi)
        self.lblAiMaxTurns.setObjectName(u"lblAiMaxTurns")

        self.aiForm.setWidget(8, QFormLayout.ItemRole.LabelRole, self.lblAiMaxTurns)

        self.spnAiMaxTurns = QSpinBox(self.tabAi)
        self.spnAiMaxTurns.setObjectName(u"spnAiMaxTurns")
        self.spnAiMaxTurns.setMinimum(1)
        self.spnAiMaxTurns.setMaximum(200)
        self.spnAiMaxTurns.setValue(10)

        self.aiForm.setWidget(8, QFormLayout.ItemRole.FieldRole, self.spnAiMaxTurns)

        self.lblAiMutationPolicy = QLabel(self.tabAi)
        self.lblAiMutationPolicy.setObjectName(u"lblAiMutationPolicy")

        self.aiForm.setWidget(9, QFormLayout.ItemRole.LabelRole, self.lblAiMutationPolicy)

        self.cbbAiMutationPolicy = QComboBox(self.tabAi)
        self.cbbAiMutationPolicy.setObjectName(u"cbbAiMutationPolicy")

        self.aiForm.setWidget(9, QFormLayout.ItemRole.FieldRole, self.cbbAiMutationPolicy)


        self.tabAiLayout.addLayout(self.aiForm)

        self.aiSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.tabAiLayout.addItem(self.aiSpacer)

        self.tabWidget.addTab(self.tabAi, "")
        self.tabAppearance = QWidget()
        self.tabAppearance.setObjectName(u"tabAppearance")
        self.tabAppearanceLayout = QVBoxLayout(self.tabAppearance)
        self.tabAppearanceLayout.setObjectName(u"tabAppearanceLayout")
        self.themeRow = QHBoxLayout()
        self.themeRow.setObjectName(u"themeRow")
        self.lblTheme = QLabel(self.tabAppearance)
        self.lblTheme.setObjectName(u"lblTheme")

        self.themeRow.addWidget(self.lblTheme)

        self.cbbTheme = QComboBox(self.tabAppearance)
        self.cbbTheme.setObjectName(u"cbbTheme")
        sizePolicy.setHeightForWidth(self.cbbTheme.sizePolicy().hasHeightForWidth())
        self.cbbTheme.setSizePolicy(sizePolicy)

        self.themeRow.addWidget(self.cbbTheme)


        self.tabAppearanceLayout.addLayout(self.themeRow)

        self.uiScaleRow = QHBoxLayout()
        self.uiScaleRow.setObjectName(u"uiScaleRow")
        self.lblUiScale = QLabel(self.tabAppearance)
        self.lblUiScale.setObjectName(u"lblUiScale")

        self.uiScaleRow.addWidget(self.lblUiScale)

        self.cbbUiScale = QComboBox(self.tabAppearance)
        self.cbbUiScale.setObjectName(u"cbbUiScale")
        sizePolicy.setHeightForWidth(self.cbbUiScale.sizePolicy().hasHeightForWidth())
        self.cbbUiScale.setSizePolicy(sizePolicy)

        self.uiScaleRow.addWidget(self.cbbUiScale)


        self.tabAppearanceLayout.addLayout(self.uiScaleRow)

        self.grpTableDisplay = QGroupBox(self.tabAppearance)
        self.grpTableDisplay.setObjectName(u"grpTableDisplay")
        self.layoutTableDisplay = QHBoxLayout(self.grpTableDisplay)
        self.layoutTableDisplay.setObjectName(u"layoutTableDisplay")
        self.cbxPathDisplayCompact = QCheckBox(self.grpTableDisplay)
        self.cbxPathDisplayCompact.setObjectName(u"cbxPathDisplayCompact")
        self.cbxPathDisplayCompact.setChecked(True)

        self.layoutTableDisplay.addWidget(self.cbxPathDisplayCompact)

        self.cbxPathHideRoot = QCheckBox(self.grpTableDisplay)
        self.cbxPathHideRoot.setObjectName(u"cbxPathHideRoot")
        self.cbxPathHideRoot.setChecked(True)

        self.layoutTableDisplay.addWidget(self.cbxPathHideRoot)

        self.tableDisplaySpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.layoutTableDisplay.addItem(self.tableDisplaySpacer)


        self.tabAppearanceLayout.addWidget(self.grpTableDisplay)

        self.appearanceSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.tabAppearanceLayout.addItem(self.appearanceSpacer)

        self.tabWidget.addTab(self.tabAppearance, "")

        self.verticalLayout.addWidget(self.tabWidget)

        self.buttonRow = QHBoxLayout()
        self.buttonRow.setObjectName(u"buttonRow")
        self.buttonSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonRow.addItem(self.buttonSpacer)

        self.btnSave = QPushButton(ProjectSettingsWindow)
        self.btnSave.setObjectName(u"btnSave")

        self.buttonRow.addWidget(self.btnSave)

        self.btnCancel = QPushButton(ProjectSettingsWindow)
        self.btnCancel.setObjectName(u"btnCancel")

        self.buttonRow.addWidget(self.btnCancel)


        self.verticalLayout.addLayout(self.buttonRow)


        self.retranslateUi(ProjectSettingsWindow)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(ProjectSettingsWindow)
    # setupUi

    def retranslateUi(self, ProjectSettingsWindow):
        ProjectSettingsWindow.setWindowTitle(QCoreApplication.translate("ProjectSettings", u"\u8bbe\u7f6e", None))
        self.cbxEnableAcronym.setText(QCoreApplication.translate("ProjectSettings", u"\u542f\u7528\u7f29\u5199\u89c4\u8303", None))
#if QT_CONFIG(tooltip)
        self.cbxEnableAcronym.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u542f\u7528\u540e\uff0c\u521b\u5efa/\u91cd\u547d\u540d\u5bf9\u8c61\u65f6\u6309\u300c\u5206\u7c7b\u547d\u540d\u4e0e\u989c\u8272\u300d\u8868\u5728\u5206\u7c7b\u5168\u540d\u4e0e\u7f29\u5199\u4e4b\u95f4\u8f6c\u6362\uff08\u5982 Character \u8f6c\u6210 CHR\uff09\uff1b\u5173\u95ed\u540e\u6240\u6709\u7f29\u5199\u8f6c\u6362\u76f4\u63a5\u8df3\u8fc7\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxEnableColor.setText(QCoreApplication.translate("ProjectSettings", u"\u542f\u7528\u989c\u8272\u89c4\u8303", None))
#if QT_CONFIG(tooltip)
        self.cbxEnableColor.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u542f\u7528\u540e\uff0c\u65b0\u5efa/\u590d\u5236\u5bf9\u8c61\u65f6\u6309\u300c\u5206\u7c7b\u547d\u540d\u4e0e\u989c\u8272\u300d\u8868\u7ed9\u5bf9\u8c61\u8bbe\u7f6e\u5bf9\u5e94\u7684 Wwise \u989c\u8272\u503c\uff1b\u5de5\u7a0b\u68c0\u67e5\u5de5\u5177\u4e2d\u7684\u300c\u989c\u8272\u4e0e\u5bf9\u8c61\u7c7b\u522b\u4e0d\u4e00\u81f4\u300d\u4e5f\u4f9d\u8d56\u6b64\u9879\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxEnableNameCase.setText(QCoreApplication.translate("ProjectSettings", u"\u542f\u7528\u540d\u79f0\u5927\u5c0f\u5199\u89c4\u8303", None))
#if QT_CONFIG(tooltip)
        self.cbxEnableNameCase.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u542f\u7528\u540e\uff0c\u5de5\u7a0b\u68c0\u67e5\u4f1a\u6309\u4e0b\u9762\u9009\u62e9\u7684\u5927\u5c0f\u5199\u65b9\u5f0f\u6821\u9a8c\u5bf9\u8c61\u540d\u5206\u6bb5\uff08\u6309 _ \u6216\u7a7a\u683c\u5206\u8bcd\uff09\uff1b\u5173\u95ed\u540e\u300c\u4e0d\u7b26\u5408\u5927\u5c0f\u5199\u89c4\u8303\u300d\u68c0\u67e5\u9879\u4e0d\u53ef\u7528\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbbNameCase.setItemText(0, QCoreApplication.translate("ProjectSettings", u"\u9996\u5b57\u6bcd\u5927\u5199", None))
        self.cbbNameCase.setItemText(1, QCoreApplication.translate("ProjectSettings", u"\u5168\u5c0f\u5199", None))
        self.cbbNameCase.setItemText(2, QCoreApplication.translate("ProjectSettings", u"\u5168\u5927\u5199", None))

#if QT_CONFIG(tooltip)
        self.cbbNameCase.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u9996\u5b57\u6bcd\u5927\u5199\uff1a\u6bcf\u4e2a\u5206\u6bb5\u9996\u5b57\u6bcd\u5927\u5199\u3001\u5176\u4f59\u4fdd\u6301\u539f\u6837\uff08\u5982 IMP_SwordToVolcano\uff09\u3002\n"
"\u5168\u5c0f\u5199\uff1a\u6bcf\u4e2a\u5206\u6bb5\u53ea\u5141\u8bb8\u5c0f\u5199\u5b57\u6bcd\u4e0e\u6570\u5b57\uff08\u5982 imp_sword\uff09\u3002\n"
"\u5168\u5927\u5199\uff1a\u6bcf\u4e2a\u5206\u6bb5\u53ea\u5141\u8bb8\u5927\u5199\u5b57\u6bcd\u4e0e\u6570\u5b57\uff08\u5982 IMP_SWORD\uff09\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxEnablePathLength.setText(QCoreApplication.translate("ProjectSettings", u"\u542f\u7528\u8def\u5f84\u957f\u5ea6\u89c4\u8303", None))
#if QT_CONFIG(tooltip)
        self.cbxEnablePathLength.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u542f\u7528\u540e\uff0c\u5de5\u7a0b\u68c0\u67e5\u4f1a\u6821\u9a8c\u540d\u79f0\u957f\u77ed\uff1aActor-Mixer \u4e0b Sound \u5e94\u4e3a\u300c\u524d\u7f00_\u63cf\u8ff0\u300d\u5f62\u5f0f\u3001\u5176\u4f59\u5bb9\u5668\u4e0d\u5e94\u5e26 _\uff0cMusic \u5c42\u7ea7\u540c\u6837\u4e0d\u5e94\u5e26 _\uff1b\u5173\u95ed\u540e\u300c\u540d\u79f0\u957f\u77ed\u4e0d\u7b26\u5408\u89c4\u8303\u300d\u68c0\u67e5\u9879\u4e0d\u53ef\u7528\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxFullNameInSound.setText(QCoreApplication.translate("ProjectSettings", u"Sound \u8282\u70b9\u4f7f\u7528\u5b8c\u6574\u540d\u79f0", None))
#if QT_CONFIG(tooltip)
        self.cbxFullNameInSound.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u8def\u5f84\u957f\u5ea6\u89c4\u8303\u7684\u4e00\u90e8\u5206\uff0c\u4ec5\u5728\u542f\u7528\u8def\u5f84\u957f\u5ea6\u89c4\u8303\u65f6\u53ef\u7528\uff1a\u521b\u5efa Play \u4e8b\u4ef6\u65f6\uff0cSound \u8282\u70b9\u5373\u4f7f\u5e26 _ \u4e5f\u76f4\u63a5\u7528\u5b8c\u6574\u540d\u79f0\u4f5c\u4e3a\u4e8b\u4ef6\u540d\uff0c\u800c\u4e0d\u662f\u518d\u62fc\u4e00\u6b21\u4e0a\u6e38\u5c42\u7ea7\u540d\u79f0\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.grpBankSettings.setTitle(QCoreApplication.translate("ProjectSettings", u"Bank\u8bbe\u7f6e", None))
        self.cbxAutoDefinedBank.setText(QCoreApplication.translate("ProjectSettings", u"\u4f7f\u7528\u81ea\u52a8\u5b9a\u4e49\u7684Bank", None))
#if QT_CONFIG(tooltip)
        self.cbxAutoDefinedBank.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u5f00\u542f\u540e\uff0cBank \u7684\u7ec4\u6210\u6309\u5de5\u5177\u81ea\u52a8\u5b9a\u4e49\u7684\u65b9\u5f0f\u751f\u6210\uff0cSoundBank \u5206\u914d\u5de5\u5177\u4e3a\u6bcf\u4e2a\u77e9\u9635\u7ec4\u5408\u521b\u5efa\u4e00\u4e2a\u540c\u65f6\u5305\u542b\u5168\u90e8\u5185\u5bb9\u7684 Bank\uff1b\u5173\u95ed\u540e\u624d\u80fd\u81ea\u884c\u9009\u62e9\u662f\u5426\u628a Event \u4e0e Media \u62c6\u6210\u4e24\u4e2a Bank\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxSplitEventMedia.setText(QCoreApplication.translate("ProjectSettings", u"Bank\u62c6\u5206Event\u548cMedia", None))
#if QT_CONFIG(tooltip)
        self.cbxSplitEventMedia.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u4ec5\u5728\u5173\u95ed\u300c\u4f7f\u7528\u81ea\u52a8\u5b9a\u4e49\u7684Bank\u300d\u65f6\u53ef\u7528\uff1a\u5f00\u542f\u540e SoundBank \u5206\u914d\u5de5\u5177\u4f1a\u4e3a\u6bcf\u4e2a\u77e9\u9635\u7ec4\u5408\u521b\u5efa _Event \u4e0e _Media \u4e24\u4e2a Bank\uff08\u5206\u522b\u5305\u542b\u4e8b\u4ef6\u7ed3\u6784\u4e0e\u5a92\u4f53\uff09\uff0c\u5173\u95ed\u65f6\u53ea\u521b\u5efa\u4e00\u4e2a\u540c\u65f6\u5305\u542b\u5168\u90e8\u5185\u5bb9\u7684 Bank\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.grpEventSettings.setTitle(QCoreApplication.translate("ProjectSettings", u"Event\u8bbe\u7f6e", None))
        self.cbxPlayPrefixInEvent.setText(QCoreApplication.translate("ProjectSettings", u"Event \u4ee5 Play_ \u5f00\u5934", None))
#if QT_CONFIG(tooltip)
        self.cbxPlayPrefixInEvent.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u72ec\u7acb\u5f00\u5173\uff0c\u4e0d\u53d7\u5176\u5b83\u89c4\u8303\u5f71\u54cd\uff1a\u5f00\u542f\u540e\u65b0\u5efa\u7684 Play \u4e8b\u4ef6\u540d\u79f0\u7edf\u4e00\u5e26 Play_ \u524d\u7f00\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxEventRefDarkColor.setText(QCoreApplication.translate("ProjectSettings", u"Event \u5f15\u7528\u4f7f\u7528\u6df1\u8272", None))
#if QT_CONFIG(tooltip)
        self.cbxEventRefDarkColor.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u4ec5\u5728\u542f\u7528\u989c\u8272\u89c4\u8303\u65f6\u53ef\u7528\uff1a\u5f00\u542f\u540e\uff0c\u300c\u66f4\u65b0\u5907\u6ce8\u4e0e\u989c\u8272\u300d\u7b49\u81ea\u52a8\u8c03\u6574\u989c\u8272\u7684\u5de5\u5177\u4f1a\u628a\u88ab Event \u64ad\u653e\uff08\u6216\u88ab SoundBank \u5305\u542b\uff09\u7684\u5bf9\u8c61\u6539\u6210\u540c\u8272\u7cfb\u7684\u6df1\u8272\u7248\u672c\uff0c\u65b9\u4fbf\u533a\u5206\u5df2\u6302\u4e8b\u4ef6\u7684\u5bf9\u8c61\uff1b\u5173\u95ed\u540e\u8fd9\u4e9b\u5bf9\u8c61\u4fdd\u6301\u666e\u901a\u5206\u7c7b\u8272\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxEventRefNotes.setText(QCoreApplication.translate("ProjectSettings", u"Event \u4e0e\u64ad\u653e\u5bf9\u8c61\u4e92\u4e3a\u5907\u6ce8", None))
#if QT_CONFIG(tooltip)
        self.cbxEventRefNotes.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u5f00\u542f\u540e\uff0c\u81ea\u52a8\u66f4\u65b0\u5907\u6ce8\u7684\u5de5\u5177\u4f1a\u628a Event \u7684\u64ad\u653e\u5bf9\u8c61\u5199\u4e0a\u300cPlayed by Event [...]\u300d\u3001Event \u5199\u4e0a\u5bf9\u8c61\u8def\u5f84\uff08\u88ab SoundBank \u5305\u542b\u7684\u5bf9\u8c61\u5199\u300cIncluded by SoundBank [...]\u300d\uff09\uff1b\u5173\u95ed\u540e\u8fd9\u4e9b\u5de5\u5177\u4e0d\u518d\u6539\u52a8 Notes\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.grpLocalizationSettings.setTitle(QCoreApplication.translate("ProjectSettings", u"\u672c\u5730\u5316\u8bbe\u7f6e", None))
        self.cbxLanguageInFileName.setText(QCoreApplication.translate("ProjectSettings", u"\u8bed\u97f3\u6587\u4ef6\u540d\u5305\u542b\u8bed\u8a00\u540d", None))
#if QT_CONFIG(tooltip)
        self.cbxLanguageInFileName.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u5f00\u542f\u540e\uff0c\u300c\u5bfc\u5165\u672c\u5730\u5316\u8bed\u8a00\u300d\u5728\u5207\u6362\u8bed\u8a00\u65f6\u4f1a\u628a\u6587\u4ef6\u540d\u4e2d\u7684\u8bed\u8a00\u540d\u4e00\u5e76\u66ff\u6362\uff08\u5982 foo_Chinese.wav \u2192 foo_English.wav\uff09\uff1b\u5173\u95ed\u65f6\u53ea\u66ff\u6362 Originals \u4e0b\u7684\u8bed\u8a00\u5b50\u76ee\u5f55\uff0c\u6587\u4ef6\u540d\u4fdd\u6301\u4e0d\u53d8\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.lblCategoryHeader.setText(QCoreApplication.translate("ProjectSettings", u"\u5206\u7c7b\u547d\u540d\u4e0e\u989c\u8272\uff08\u5206\u7c7b\u540d \u2192 \u7f29\u5199 / Wwise \u989c\u8272\u503c\uff09", None))
        self.lblContainerHeader.setText(QCoreApplication.translate("ProjectSettings", u"\u5bb9\u5668\u5b50\u8282\u70b9\u540e\u7f00\uff08\u6b63\u5219\u8868\u8fbe\u5f0f\uff09", None))
        self.lblGroupHeader.setText(QCoreApplication.translate("ProjectSettings", u"\u89d2\u82721P/2P/3P SwitchGroup \u540d\u79f0", None))
#if QT_CONFIG(tooltip)
        self.netRoleValues.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u89d2\u8272\uff1a1P\uff08\u4e3b\u89d2\uff09/2P\uff08\u961f\u53cb\uff09/3P\uff08\u654c\u4eba\uff09\u3002Switch \u540d\u79f0\uff1a\u5bf9\u5e94\u7684 Switch \u5206\u652f\u540d\u3002\u5bf9\u8c61\u540d\u540e\u7f00\uff1a\u62c6\u5206\u65f6\u8be5\u89d2\u8272\u5bf9\u8c61\u7684\u540d\u79f0\u540e\u7f00\u3002Bus\u540e\u7f00\uff1a\u8be5\u89d2\u8272 Bus \u7684\u540d\u79f0\u540e\u7f00\uff1b\u628a 2P \u7684 Bus \u540e\u7f00\u586b\u6210 3P \u7684\u540e\u7f00\u5373\u8868\u793a\u4e0d\u533a\u5206 2P/3P Bus\uff0c\u4e24\u8005\u590d\u7528\u540c\u4e00\u4e2a Bus\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabNaming), QCoreApplication.translate("ProjectSettings", u"\u5de5\u7a0b\u89c4\u8303", None))
        self.grpSearchAndFilter.setTitle(QCoreApplication.translate("ProjectSettings", u"\u67e5\u627e\u4e0e\u7b5b\u9009", None))
        self.cbxAutoFetchChildren.setText(QCoreApplication.translate("ProjectSettings", u"\u5de5\u5177\u6267\u884c\u524d\u81ea\u52a8\u83b7\u53d6\u5b50\u5bf9\u8c61", None))
        self.cbxFindFilterCheckedOnly.setText(QCoreApplication.translate("ProjectSettings", u"\u67e5\u627e/\u7b5b\u9009\u53ea\u5bf9\u9009\u4e2d\u5bf9\u8c61\u751f\u6548", None))
#if QT_CONFIG(tooltip)
        self.cbxFindFilterCheckedOnly.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u52fe\u9009\u540e\uff0c\u627e\u7236\u7ea7/\u627e\u5b50\u7ea7/\u627e\u5f15\u7528/\u9ad8\u7ea7\u67e5\u627e\u4ee5\u53ca\u8868\u683c\u7b5b\u9009\u53ea\u5904\u7406\u300c\u9009\u4e2d\u300d\u5217\u52fe\u9009\u7684\u884c\uff0c\u672a\u52fe\u9009\u7684\u884c\u539f\u6837\u4fdd\u7559\u5e76\u59cb\u7ec8\u663e\u793a\uff1b\u53d6\u6d88\u52fe\u9009\u5219\u5bf9\u5168\u90e8\u53ef\u89c1\u884c\u751f\u6548\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxKeepSelf.setText(QCoreApplication.translate("ProjectSettings", u"\u4fdd\u7559\u539f\u59cb\u5c42\u7ea7", None))
#if QT_CONFIG(tooltip)
        self.cbxKeepSelf.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u9ad8\u7ea7\u67e5\u627e\u5b50\u5bf9\u8c61\u65f6\uff0c\u67e5\u627e\u7ed3\u679c\u540c\u65f6\u4fdd\u7559\u8f93\u5165\u5bf9\u8c61\u81ea\u8eab\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.lblPageSize.setText(QCoreApplication.translate("ProjectSettings", u"\u67e5\u8be2\u5206\u9875\u5927\u5c0f", None))
#if QT_CONFIG(tooltip)
        self.lblPageSize.setToolTip(QCoreApplication.translate("ProjectSettings", u"WAAPI \u67e5\u8be2\u5b50\u5bf9\u8c61/\u540e\u4ee3/\u6279\u91cf\u67e5\u627e\u65f6\u6bcf\u6b21\u62c9\u53d6\u7684\u6570\u91cf\u3002\u8c03\u5927\u80fd\u51cf\u5c11\u8bf7\u6c42\u6b21\u6570\uff0c\u4f46\u5355\u6b21\u8bf7\u6c42\u66f4\u91cd\uff1b\u4e3b\u7a97\u53e3\u67e5\u627e\u5bf9\u8c61\u4e0e\u5404\u5de5\u5177\u5171\u7528\u8be5\u503c\u3002", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.spbPageSize.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u9ed8\u8ba4 500\uff0c\u53ef\u8c03\u8303\u56f4 50-5000\u3002\u5bf9\u8c61\u6570\u91cf\u5f88\u5927\u7684\u5de5\u7a0b\u5efa\u8bae\u4fdd\u6301 500 \u5de6\u53f3\uff0c\u907f\u514d\u5355\u6b21\u8bf7\u6c42\u8d85\u65f6\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxCaseSensitive.setText(QCoreApplication.translate("ProjectSettings", u"\u533a\u5206\u5927\u5c0f\u5199", None))
#if QT_CONFIG(tooltip)
        self.cbxCaseSensitive.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u4e3b\u7a97\u53e3\u8868\u683c\u5173\u952e\u8bcd\u7b5b\u9009\u65f6\u533a\u5206\u82f1\u6587\u5b57\u6bcd\u5927\u5c0f\u5199\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxOnlyIncluded.setText(QCoreApplication.translate("ProjectSettings", u"\u4ec5\u663e\u793a\u542f\u7528\u5bf9\u8c61", None))
#if QT_CONFIG(tooltip)
        self.cbxOnlyIncluded.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u8fc7\u6ee4\u6389\u5de5\u7a0b\u4e2d\u672a\u542f\u7528\u7684\u5bf9\u8c61\uff08\u542b\u4e0a\u7ea7\u672a\u542f\u7528\u7684\u5c42\u7ea7\uff09\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxOnlyInUse.setText(QCoreApplication.translate("ProjectSettings", u"\u53ea\u663e\u793a\u5728\u7528\u8d44\u6e90", None))
#if QT_CONFIG(tooltip)
        self.cbxOnlyInUse.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u53ea\u663e\u793a\u88ab WorkUnit \u5185\u5f53\u524d\u8bed\u8a00\u5b9e\u9645\u5f15\u7528\u7684\u97f3\u9891\u6e90\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.lblEventFilter.setText(QCoreApplication.translate("ProjectSettings", u"Event\u5f15\u7528\uff1a", None))
        self.rbnEventAll.setText(QCoreApplication.translate("ProjectSettings", u"\u5168\u90e8", None))
        self.rbnEventHas.setText(QCoreApplication.translate("ProjectSettings", u"\u6709\u5f15\u7528", None))
        self.rbnEventNo.setText(QCoreApplication.translate("ProjectSettings", u"\u65e0\u5f15\u7528", None))
        self.lblLanguageFilter.setText(QCoreApplication.translate("ProjectSettings", u"\u8bed\u8a00\u7b5b\u9009\uff1a", None))
        self.rbnLangAll.setText(QCoreApplication.translate("ProjectSettings", u"\u5168\u90e8\u8bed\u8a00", None))
        self.rbnLangActive.setText(QCoreApplication.translate("ProjectSettings", u"\u4ec5\u5f53\u524d\u8bed\u8a00", None))
#if QT_CONFIG(tooltip)
        self.cbxDetailLog.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u6253\u5f00\u540e\u4f1a\u628a\u6279\u91cf\u5904\u7406\u4e2d\u6bcf\u4e2a\u5bf9\u8c61\u7684\u5904\u7406\u8bb0\u5f55\u3001\u4ee5\u53ca\u6bcf\u6b21 WAAPI \u8c03\u7528\u7684\u53c2\u6570\u4e0e\u8017\u65f6\u5199\u8fdb\u65e5\u5fd7\u6587\u4ef6\uff08gui_log.log / mcp_log.log\uff09\u3002\u65e5\u5fd7\u91cf\u5927\u65f6\u4f1a\u4ea7\u751f\u989d\u5916\u78c1\u76d8\u5199\u5165\uff0c\u6392\u67e5\u95ee\u9898\u540e\u518d\u5173\u6389\u5373\u53ef\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxDetailLog.setText(QCoreApplication.translate("ProjectSettings", u"\u8bb0\u5f55\u660e\u7ec6\u65e5\u5fd7\uff08\u6279\u91cf\u9010\u5bf9\u8c61\u3001WAAPI \u8c03\u7528\u6d41\u6c34\uff09", None))
#if QT_CONFIG(tooltip)
        self.cbxDumpOnlyWritable.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u52fe\u9009\u65f6\uff0c\u300c\u5bfc\u51fa\u5168\u90e8\u5c5e\u6027\uff08JSON\uff09\u300d\u53ea\u5199\u53ef\u5199\u5c5e\u6027\uff1a\u8df3\u8fc7 id/name/path/children/descendants \u7b49\u53ea\u8bfb\u8bbf\u95ee\u5668\uff0c\u4ee5\u53ca\u5217\u8868\u3001\u65e0 id \u7684\u590d\u5408\u503c\uff1b\u53d6\u6d88\u52fe\u9009\u5219\u5bfc\u51fa schema \u91cc\u7684\u5168\u90e8\u5c5e\u6027\u503c\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxDumpOnlyWritable.setText(QCoreApplication.translate("ProjectSettings", u"\u5bfc\u51fa\u5c5e\u6027\u65f6\u4ec5\u5305\u542b\u53ef\u5199\u5c5e\u6027", None))
        self.grpConversion.setTitle(QCoreApplication.translate("ProjectSettings", u"\u81ea\u52a8\u8f6c\u7801", None))
        self.lblConversionDominance.setText(QCoreApplication.translate("ProjectSettings", u"\u957f\u77ed\u97f3\u6548\u5360\u4f18\u6bd4\u4f8b", None))
#if QT_CONFIG(tooltip)
        self.lblConversionDominance.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u81ea\u52a8\u8f6c\u7801\u65f6\uff0c\u67d0\u4e2a\u8282\u70b9\u4e0a\u7684\u957f/\u77ed\u97f3\u6548\u5360\u6bd4\u8981\u4e25\u683c\u8d85\u8fc7\u8be5\u6bd4\u4f8b\uff0c\u624d\u4f1a\u8986\u76d6\u4e0a\u5c42\u8bbe\u7f6e\uff1b\u5360\u6bd4\u4e0d\u591f\u660e\u663e\uff08\u5982 40:60\uff09\u65f6\u7ee7\u627f\u4e0a\u5c42\uff0c\u4ea4\u7ed9\u66f4\u4e0b\u5c42\u7684\u8282\u70b9\u51b3\u5b9a\u3002\u9ed8\u8ba4 60%\uff0c\u5373 40:60 \u5206\u754c\u3002", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.spbConversionDominance.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u81ea\u52a8\u8f6c\u7801\u65f6\uff0c\u67d0\u4e2a\u8282\u70b9\u4e0a\u7684\u957f/\u77ed\u97f3\u6548\u5360\u6bd4\u8981\u4e25\u683c\u8d85\u8fc7\u8be5\u6bd4\u4f8b\uff0c\u624d\u4f1a\u8986\u76d6\u4e0a\u5c42\u8bbe\u7f6e\uff1b\u5360\u6bd4\u4e0d\u591f\u660e\u663e\uff08\u5982 40:60\uff09\u65f6\u7ee7\u627f\u4e0a\u5c42\uff0c\u4ea4\u7ed9\u66f4\u4e0b\u5c42\u7684\u8282\u70b9\u51b3\u5b9a\u3002\u9ed8\u8ba4 60%\uff0c\u5373 40:60 \u5206\u754c\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.spbConversionDominance.setSuffix(QCoreApplication.translate("ProjectSettings", u" %", None))
        self.grpLoudness.setTitle(QCoreApplication.translate("ProjectSettings", u"\u54cd\u5ea6\u8bbe\u7f6e", None))
        self.lblLoudnessStandard.setText(QCoreApplication.translate("ProjectSettings", u"\u54cd\u5ea6\u6807\u51c6", None))
        self.cbbLoudnessStandard.setItemText(0, QCoreApplication.translate("ProjectSettings", u"RMS", None))
        self.cbbLoudnessStandard.setItemText(1, QCoreApplication.translate("ProjectSettings", u"LUFS", None))

        self.lblTargetLoudness.setText(QCoreApplication.translate("ProjectSettings", u"\u76ee\u6807\u54cd\u5ea6", None))
        self.spbTargetLoudness.setSuffix(QCoreApplication.translate("ProjectSettings", u" dBFS", None))
        self.lblLoudnessTolerance.setText(QCoreApplication.translate("ProjectSettings", u"\u5bbd\u5bb9\u5ea6", None))
        self.spbLoudnessTolerance.setSuffix(QCoreApplication.translate("ProjectSettings", u" dB", None))
        self.grpLocalization.setTitle(QCoreApplication.translate("ProjectSettings", u"\u672c\u5730\u5316", None))
        self.lblReferenceLanguage.setText(QCoreApplication.translate("ProjectSettings", u"\u53c2\u8003\u8bed\u8a00", None))
        self.cbxUseDefaultReferenceLanguage.setText(QCoreApplication.translate("ProjectSettings", u"\u4f7f\u7528\u5de5\u7a0b\u9ed8\u8ba4", None))
#if QT_CONFIG(tooltip)
        self.cbxUseDefaultReferenceLanguage.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u52fe\u9009\u540e\u76f4\u63a5\u8bfb\u53d6 Wwise \u5de5\u7a0b\u7684\u53c2\u8003\u8bed\u8a00\uff08referenceLanguageId\uff09\uff1b\u53d6\u6d88\u52fe\u9009\u5219\u4f7f\u7528\u53f3\u8fb9\u624b\u586b\u7684\u8bed\u8a00\u540d\uff0c\u9759\u97f3\u586b\u8865\u7a7a\u7f3a\u7b49\u672c\u5730\u5316\u5de5\u5177\u4e0e\u591a\u8bed\u8a00\u5bf9\u6bd4\u90fd\u4f1a\u7528\u5230\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.ledReferenceLanguage.setPlaceholderText(QCoreApplication.translate("ProjectSettings", u"\u4f8b\u5982 EN", None))
        self.lblLanguagesHeader.setText(QCoreApplication.translate("ProjectSettings", u"\u672a\u63a5\u5165\u8bed\u8a00\uff08\u7528\u5206\u53f7\u5206\u9694\uff09", None))
#if QT_CONFIG(tooltip)
        self.lblLanguagesHeader.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u8fd9\u4e9b\u8bed\u8a00\u5c1a\u672a\u63a5\u5165\uff0c\u5de5\u7a0b\u68c0\u67e5\u65f6\u4e0d\u4f1a\u8981\u6c42\u5b83\u4eec\u5b58\u5728\u5bf9\u5e94\u8bed\u97f3\uff0c\u4e5f\u4e0d\u53c2\u4e0e\u672c\u5730\u5316\u68c0\u67e5\u3002\u591a\u4e2a\u8bed\u8a00\u7528\u5206\u53f7\u5206\u9694\uff0c\u4f8b\u5982 Chinese;Japanese\u3002", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.iptLanguages.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u591a\u4e2a\u8bed\u8a00\u7528\u5206\u53f7\u5206\u9694\uff0c\u4f8b\u5982 Chinese;Japanese\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.lblSilenceDuration.setText(QCoreApplication.translate("ProjectSettings", u"\u9759\u97f3\u586b\u8865\u65f6\u957f", None))
#if QT_CONFIG(tooltip)
        self.lblSilenceDuration.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u300c\u9759\u97f3\u586b\u8865\u7a7a\u7f3a\u300d\u4e3a\u7f3a\u5931\u8bed\u8a00\u65b0\u5efa\u7684\u9759\u97f3\u6e90\u957f\u5ea6\uff08\u79d2\uff09\u3002", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.spbSilenceDuration.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u9ed8\u8ba4 2 \u79d2\uff0c\u53ef\u8c03\u8303\u56f4 0.1-60\u3002\u53ea\u5f71\u54cd\u65b0\u5efa\u7684\u9759\u97f3\u6e90\uff0c\u5df2\u6709\u6837\u672c\u4e0d\u53d7\u5f71\u54cd\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.spbSilenceDuration.setSuffix(QCoreApplication.translate("ProjectSettings", u" \u79d2", None))
        self.grpAudioPreview.setTitle(QCoreApplication.translate("ProjectSettings", u"\u97f3\u9891\u5206\u6790\u4e0e\u9884\u89c8", None))
        self.lblPreviewDisplayMode.setText(QCoreApplication.translate("ProjectSettings", u"\u663e\u793a\u6a21\u5f0f", None))
        self.cbbPreviewDisplayMode.setItemText(0, QCoreApplication.translate("ProjectSettings", u"\u6ce2\u5f62", None))
        self.cbbPreviewDisplayMode.setItemText(1, QCoreApplication.translate("ProjectSettings", u"\u9891\u8c31", None))

        self.lblLoudnessBuffer.setText(QCoreApplication.translate("ProjectSettings", u"\u54cd\u5ea6\u5206\u6790\u5206\u5757\u91c7\u6837\u70b9", None))
#if QT_CONFIG(tooltip)
        self.lblLoudnessBuffer.setToolTip(QCoreApplication.translate("ProjectSettings", u"RMS \u54cd\u5ea6\u5206\u6790\u65f6\u6bcf\u4e2a buffer \u7684\u91c7\u6837\u70b9\u6570\uff1a\u6bcf buffer \u5355\u72ec\u6c42\u529f\u7387\uff0c\u5254\u9664\u4f4e\u4e8e\u95e8\u9650\u7684\u9759\u97f3 buffer \u540e\u518d\u53d6\u5e73\u5747\u3002\u5206\u5757\u8d8a\u5927\u8d8a\u63a5\u8fd1\u6574\u4f53\u54cd\u5ea6\uff0c\u8d8a\u5c0f\u5bf9\u9759\u97f3\u6bb5\u66f4\u654f\u611f\u3002", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.spbLoudnessBuffer.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u9ed8\u8ba4 1024\uff0c\u53ef\u8c03\u8303\u56f4 128-65536\u3002\u54cd\u5ea6\u8c03\u6574\u3001\u9759\u97f3\u88c1\u526a\u3001\u97f3\u9891\u9884\u89c8\u7684\u54cd\u5ea6\u663e\u793a\u5171\u7528\u8be5\u503c\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.grpRandomCount.setTitle(QCoreApplication.translate("ProjectSettings", u"\u4f18\u5316\u968f\u673a\u6570\u91cf", None))
        self.lblRandomCountHint.setText(QCoreApplication.translate("ProjectSettings", u"\u6bcf\u4e2a\u5e73\u53f0\u4e00\u5217\uff0c\u8bbe\u7f6e\u5141\u8bb8\u4fdd\u7559\u542f\u7528\u7684 Random Container \u5b50\u5bf9\u8c61\u6570\u91cf\uff1b\u672a\u5355\u72ec\u914d\u7f6e\u7684\u5e73\u53f0\u4f7f\u7528\u9ed8\u8ba4\u503c 3\u3002", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabTools), QCoreApplication.translate("ProjectSettings", u"\u5de5\u5177\u884c\u4e3a", None))
        self.lblVcsMode.setText(QCoreApplication.translate("ProjectSettings", u"\u7248\u672c\u63a7\u5236\u7c7b\u578b", None))
#if QT_CONFIG(tooltip)
        self.cbbVcsMode.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u7528\u4e8e\u4e3b\u7a97\u53e3\u300c\u96c6\u6210\u89c6\u56fe - \u4f5c\u8005\u300d\u5217\uff1a\u8bfb\u53d6\u5bf9\u8c61\u6240\u5728 WorkUnit \u6700\u540e\u4e00\u6b21\u63d0\u4ea4\u7684\u63d0\u4ea4\u4eba\u3002SVN \u8bfb\u672c\u5730\u5de5\u4f5c\u526f\u672c\uff08\u8f83\u5feb\uff09\uff1bP4 \u9700\u8fde\u63a5\u670d\u52a1\u5668\uff08\u9996\u6b21\u8f83\u6162\uff09\u3002\u4fee\u6539\u540e\u9700\u91cd\u542f\u8f6f\u4ef6\u751f\u6548\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.lblP4Server.setText(QCoreApplication.translate("ProjectSettings", u"P4 \u670d\u52a1\u5668", None))
        self.iptP4Server.setPlaceholderText(QCoreApplication.translate("ProjectSettings", u"\u5982 ssl:perforce.example.com:1666\uff1b\u7559\u7a7a\u8868\u793a\u7528 P4 \u5ba2\u6237\u7aef\u9ed8\u8ba4\u503c", None))
        self.lblP4Charset.setText(QCoreApplication.translate("ProjectSettings", u"P4 \u5b57\u7b26\u96c6", None))
        self.iptP4Charset.setPlaceholderText(QCoreApplication.translate("ProjectSettings", u"\u9ed8\u8ba4 utf8", None))
        self.lblP4ChangelistDescription.setText(QCoreApplication.translate("ProjectSettings", u"P4 \u63d0\u4ea4\u63cf\u8ff0", None))
        self.lblSvnExecutable.setText(QCoreApplication.translate("ProjectSettings", u"SVN \u53ef\u6267\u884c\u6587\u4ef6", None))
        self.iptSvnExecutable.setPlaceholderText(QCoreApplication.translate("ProjectSettings", u"\u5df2\u5728 PATH \u4e2d\u65f6\u76f4\u63a5\u5199 svn\uff0c\u5426\u5219\u5199\u5b8c\u6574\u8def\u5f84", None))
        self.lblSvnUsername.setText(QCoreApplication.translate("ProjectSettings", u"SVN \u7528\u6237\u540d", None))
        self.lblSvnPassword.setText(QCoreApplication.translate("ProjectSettings", u"SVN \u5bc6\u7801", None))
        self.lblSvnCommitMessage.setText(QCoreApplication.translate("ProjectSettings", u"SVN \u63d0\u4ea4\u4fe1\u606f", None))
        self.btnVcsTest.setText(QCoreApplication.translate("ProjectSettings", u"\u6d4b\u8bd5\u8fde\u63a5", None))
#if QT_CONFIG(tooltip)
        self.btnVcsTest.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u7528\u5f53\u524d\u914d\u7f6e\u8bfb\u53d6\u4e00\u6b21\u7248\u672c\u4fe1\u606f\uff0c\u9a8c\u8bc1\u670d\u52a1\u5668\u3001\u5de5\u4f5c\u526f\u672c\u4e0e\u8d26\u53f7\u662f\u5426\u53ef\u7528\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabVersionControl), QCoreApplication.translate("ProjectSettings", u"\u7248\u672c\u63a7\u5236", None))
        self.lblAiMode.setText(QCoreApplication.translate("ProjectSettings", u"\u8fde\u63a5\u6a21\u5f0f", None))
#if QT_CONFIG(tooltip)
        self.cbbAiMode.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u4ee3\u7406\u6a21\u5f0f\u8d70\u672c\u5730/\u516c\u53f8\u4ee3\u7406\u5730\u5740\uff1b\u5b98\u65b9 API \u6a21\u5f0f\u6309\u300c\u670d\u52a1\u63d0\u4f9b\u65b9\u300d\u76f4\u8fde\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.lblAiProvider.setText(QCoreApplication.translate("ProjectSettings", u"\u670d\u52a1\u63d0\u4f9b\u65b9", None))
#if QT_CONFIG(tooltip)
        self.cbbAiProvider.setToolTip(QCoreApplication.translate("ProjectSettings", u"Claude \u4f7f\u7528 Anthropic \u539f\u751f\u534f\u8bae\uff0c\u5fc5\u987b\u586b\u5199\u6a21\u578b\u540d\uff1b\u5176\u4f59\u5382\u5546\u8d70 OpenAI \u517c\u5bb9\u534f\u8bae\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.lblAiProxy.setText(QCoreApplication.translate("ProjectSettings", u"\u4ee3\u7406\u5730\u5740", None))
        self.iptAiProxy.setPlaceholderText(QCoreApplication.translate("ProjectSettings", u"http://127.0.0.1:15721", None))
        self.lblAiBaseUrl.setText(QCoreApplication.translate("ProjectSettings", u"\u81ea\u5b9a\u4e49\u5730\u5740", None))
        self.iptAiBaseUrl.setPlaceholderText(QCoreApplication.translate("ProjectSettings", u"\u5b98\u65b9\u6a21\u5f0f\u9009\u62e9\u201c\u81ea\u5b9a\u4e49\u201d\u65f6\u586b\u5199\uff0c\u5982 https://api.example.com", None))
        self.lblAiApiKey.setText(QCoreApplication.translate("ProjectSettings", u"API Key", None))
        self.lblAiModel.setText(QCoreApplication.translate("ProjectSettings", u"\u6a21\u578b", None))
        self.iptAiModel.setPlaceholderText(QCoreApplication.translate("ProjectSettings", u"\u5b98\u65b9\u6a21\u5f0f\u5efa\u8bae\u586b\u5199\uff08Claude \u5fc5\u586b\uff09\uff1b\u4ee3\u7406\u6a21\u5f0f\u53ef\u7559\u7a7a", None))
        self.cbxAiEnableScript.setText(QCoreApplication.translate("ProjectSettings", u"\u5141\u8bb8 AI \u6267\u884c\u4e34\u65f6\u811a\u672c\uff08run_wwise_script\uff09", None))
#if QT_CONFIG(tooltip)
        self.cbxAiEnableScript.setToolTip(QCoreApplication.translate("ProjectSettings", u"IDE \u8c03\u8bd5\u5668\u4e0b\u53ef\u80fd\u4e0d\u7a33\u5b9a\uff0c\u9ed8\u8ba4\u5173\u95ed\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.lblAiMaxContext.setText(QCoreApplication.translate("ProjectSettings", u"\u5355\u6b21\u6700\u5927\u5bf9\u8c61\u6570", None))
        self.lblAiMaxTurns.setText(QCoreApplication.translate("ProjectSettings", u"\u6700\u5927\u5bf9\u8bdd\u8f6e\u6570", None))
        self.lblAiMutationPolicy.setText(QCoreApplication.translate("ProjectSettings", u"\u4fee\u6539\u7b56\u7565", None))
#if QT_CONFIG(tooltip)
        self.cbbAiMutationPolicy.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u53ea\u8bfb\uff1d\u62d2\u7edd\u4e00\u5207\u6539\u52a8\uff1b\u6539\u52a8\u524d\u5f39\u7a97\u786e\u8ba4\uff1dAI \u6539\u5de5\u7a0b\u524d\u7531\u4f60\u70b9\u786e\u8ba4\uff1b\u76f4\u63a5\u6267\u884c\uff1d\u4e0d\u518d\u8be2\u95ee\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabAi), QCoreApplication.translate("ProjectSettings", u"AI \u52a9\u624b", None))
        self.lblTheme.setText(QCoreApplication.translate("ProjectSettings", u"\u754c\u9762\u4e3b\u9898", None))
        self.lblUiScale.setText(QCoreApplication.translate("ProjectSettings", u"\u754c\u9762\u7f29\u653e", None))
#if QT_CONFIG(tooltip)
        self.lblUiScale.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u8ddf\u968f\u7cfb\u7edf\uff1d\u6309 Windows \u7684\u663e\u793a\u7f29\u653e\u663e\u793a\uff1b\u9009\u62e9\u5177\u4f53\u767e\u5206\u6bd4\u5219\u56fa\u5b9a\u4e3a\u8be5\u7f29\u653e\uff08\u4e0d\u518d\u8ddf\u968f\u7cfb\u7edf\uff09\u3002QT_SCALE_FACTOR \u53ea\u5728\u542f\u52a8\u65f6\u751f\u6548\uff0c\u6539\u5b8c\u9700\u8981\u91cd\u542f\u8f6f\u4ef6\u3002", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.cbbUiScale.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u754c\u9762\u611f\u89c9\u6574\u4f53\u88ab\u653e\u5927\uff08\u6216\u60f3\u56fa\u5b9a\u4e0d\u653e\u5927\uff09\u65f6\uff0c\u53ef\u5728\u8fd9\u91cc\u9009 100% \u5e76\u91cd\u542f\uff1b\u5c4f\u5e55\u672c\u8eab\u662f\u9ad8\u5206\u5c4f\u65f6\u9009\u300c\u8ddf\u968f\u7cfb\u7edf\u300d\u6700\u5408\u9002\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.grpTableDisplay.setTitle(QCoreApplication.translate("ProjectSettings", u"\u8868\u683c\u663e\u793a", None))
        self.cbxPathDisplayCompact.setText(QCoreApplication.translate("ProjectSettings", u"\u8868\u683c\u8def\u5f84\u663e\u793a\u5173\u952e\u8bcd\u53bb\u91cd\u540e\u7684\u7b80\u5199", None))
#if QT_CONFIG(tooltip)
        self.cbxPathHideRoot.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u52fe\u9009\u540e\u53bb\u6389\u8def\u5f84\u5f00\u5934\u7684\u6839\u76ee\u5f55\uff08\u5982 \\Actor-Mixer Hierarchy\u3001\\Events\uff09\uff0c\u6240\u6709\u8868\u683c\u4e0e\u5de5\u5177\u7a97\u53e3\u5171\u7528\u8be5\u663e\u793a\u89c4\u5219\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxPathHideRoot.setText(QCoreApplication.translate("ProjectSettings", u"\u8def\u5f84\u9690\u85cf\u6839\u76ee\u5f55", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabAppearance), QCoreApplication.translate("ProjectSettings", u"\u5916\u89c2", None))
        self.btnSave.setText(QCoreApplication.translate("ProjectSettings", u"\u4fdd\u5b58", None))
        self.btnCancel.setText(QCoreApplication.translate("ProjectSettings", u"\u53d6\u6d88", None))
    # retranslateUi

