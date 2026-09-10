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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
    QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QSpinBox, QTabWidget, QVBoxLayout,
    QWidget)

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

        self.cbxEventRefDarkColor = QCheckBox(self.tabNaming)
        self.cbxEventRefDarkColor.setObjectName(u"cbxEventRefDarkColor")
        self.cbxEventRefDarkColor.setChecked(True)

        self.regulationSwitches.addWidget(self.cbxEventRefDarkColor, 1, 1, 1, 1)

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

        self.cbxPlayPrefixInEvent = QCheckBox(self.tabNaming)
        self.cbxPlayPrefixInEvent.setObjectName(u"cbxPlayPrefixInEvent")

        self.regulationSwitches.addWidget(self.cbxPlayPrefixInEvent, 0, 5, 1, 1)

        self.cbxEventRefNotes = QCheckBox(self.tabNaming)
        self.cbxEventRefNotes.setObjectName(u"cbxEventRefNotes")
        self.cbxEventRefNotes.setChecked(True)

        self.regulationSwitches.addWidget(self.cbxEventRefNotes, 1, 5, 1, 1)

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
        self.cbxAutoFetchChildren = QCheckBox(self.tabTools)
        self.cbxAutoFetchChildren.setObjectName(u"cbxAutoFetchChildren")

        self.tabToolsLayout.addWidget(self.cbxAutoFetchChildren)

        self.pageSizeRow = QHBoxLayout()
        self.pageSizeRow.setObjectName(u"pageSizeRow")
        self.lblPageSize = QLabel(self.tabTools)
        self.lblPageSize.setObjectName(u"lblPageSize")

        self.pageSizeRow.addWidget(self.lblPageSize)

        self.spbPageSize = QSpinBox(self.tabTools)
        self.spbPageSize.setObjectName(u"spbPageSize")
        self.spbPageSize.setMinimum(50)
        self.spbPageSize.setMaximum(5000)
        self.spbPageSize.setSingleStep(50)
        self.spbPageSize.setValue(500)

        self.pageSizeRow.addWidget(self.spbPageSize)

        self.pageSizeSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.pageSizeRow.addItem(self.pageSizeSpacer)


        self.tabToolsLayout.addLayout(self.pageSizeRow)

        self.lblLanguagesHeader = QLabel(self.tabTools)
        self.lblLanguagesHeader.setObjectName(u"lblLanguagesHeader")

        self.tabToolsLayout.addWidget(self.lblLanguagesHeader)

        self.iptLanguages = QLineEdit(self.tabTools)
        self.iptLanguages.setObjectName(u"iptLanguages")

        self.tabToolsLayout.addWidget(self.iptLanguages)

        self.toolsSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.tabToolsLayout.addItem(self.toolsSpacer)

        self.tabWidget.addTab(self.tabTools, "")
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


        self.tabAiLayout.addLayout(self.aiForm)

        self.lblAiHint = QLabel(self.tabAi)
        self.lblAiHint.setObjectName(u"lblAiHint")
        self.lblAiHint.setWordWrap(True)

        self.tabAiLayout.addWidget(self.lblAiHint)

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

        self.cbxPathDisplayCompact = QCheckBox(self.tabAppearance)
        self.cbxPathDisplayCompact.setObjectName(u"cbxPathDisplayCompact")
        self.cbxPathDisplayCompact.setChecked(True)

        self.tabAppearanceLayout.addWidget(self.cbxPathDisplayCompact)

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
        self.cbxEventRefDarkColor.setText(QCoreApplication.translate("ProjectSettings", u"Event \u5f15\u7528\u4f7f\u7528\u6df1\u8272", None))
#if QT_CONFIG(tooltip)
        self.cbxEventRefDarkColor.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u542f\u7528\u540e\uff0c\u300c\u66f4\u65b0\u5907\u6ce8\u4e0e\u989c\u8272\u300d\u7b49\u81ea\u52a8\u8c03\u6574\u989c\u8272\u7684\u5de5\u5177\u4f1a\u628a\u88ab Event \u64ad\u653e\uff08\u6216\u88ab SoundBank \u5305\u542b\uff09\u7684\u5bf9\u8c61\u6539\u6210\u540c\u8272\u7cfb\u7684\u6df1\u8272\u7248\u672c\uff0c\u65b9\u4fbf\u533a\u5206\u5df2\u6302\u4e8b\u4ef6\u7684\u5bf9\u8c61\uff1b\u5173\u95ed\u540e\u8fd9\u4e9b\u5bf9\u8c61\u4fdd\u6301\u666e\u901a\u5206\u7c7b\u8272\u3002", None))
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
        self.cbxPlayPrefixInEvent.setText(QCoreApplication.translate("ProjectSettings", u"Event \u4ee5 Play_ \u5f00\u5934", None))
#if QT_CONFIG(tooltip)
        self.cbxPlayPrefixInEvent.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u72ec\u7acb\u5f00\u5173\uff0c\u4e0d\u53d7\u5176\u5b83\u89c4\u8303\u5f71\u54cd\uff1a\u5f00\u542f\u540e\u65b0\u5efa\u7684 Play \u4e8b\u4ef6\u540d\u79f0\u7edf\u4e00\u5e26 Play_ \u524d\u7f00\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxEventRefNotes.setText(QCoreApplication.translate("ProjectSettings", u"Event \u4e0e\u64ad\u653e\u5bf9\u8c61\u4e92\u4e3a\u5907\u6ce8", None))
#if QT_CONFIG(tooltip)
        self.cbxEventRefNotes.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u5f00\u542f\u540e\uff0c\u81ea\u52a8\u66f4\u65b0\u5907\u6ce8\u7684\u5de5\u5177\u4f1a\u628a Event \u7684\u64ad\u653e\u5bf9\u8c61\u5199\u4e0a\u300cPlayed by Event [...]\u300d\u3001Event \u5199\u4e0a\u5bf9\u8c61\u8def\u5f84\uff08\u88ab SoundBank \u5305\u542b\u7684\u5bf9\u8c61\u5199\u300cIncluded by SoundBank [...]\u300d\uff09\uff1b\u5173\u95ed\u540e\u8fd9\u4e9b\u5de5\u5177\u4e0d\u518d\u6539\u52a8 Notes\u3002", None))
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
        self.lblCategoryHeader.setText(QCoreApplication.translate("ProjectSettings", u"\u5206\u7c7b\u547d\u540d\u4e0e\u989c\u8272\uff08\u5206\u7c7b\u540d \u2192 \u7f29\u5199 / Wwise \u989c\u8272\u503c\uff09", None))
        self.lblContainerHeader.setText(QCoreApplication.translate("ProjectSettings", u"\u5bb9\u5668\u5b50\u8282\u70b9\u540e\u7f00\uff08\u6b63\u5219\u8868\u8fbe\u5f0f\uff09", None))
        self.lblGroupHeader.setText(QCoreApplication.translate("ProjectSettings", u"\u89d2\u82721P/2P/3P SwitchGroup \u540d\u79f0", None))
#if QT_CONFIG(tooltip)
        self.netRoleValues.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u89d2\u8272\uff1a1P\uff08\u4e3b\u89d2\uff09/2P\uff08\u961f\u53cb\uff09/3P\uff08\u654c\u4eba\uff09\u3002Switch \u540d\u79f0\uff1a\u5bf9\u5e94\u7684 Switch \u5206\u652f\u540d\u3002\u5bf9\u8c61\u540d\u540e\u7f00\uff1a\u62c6\u5206\u65f6\u8be5\u89d2\u8272\u5bf9\u8c61\u7684\u540d\u79f0\u540e\u7f00\u3002Bus\u540e\u7f00\uff1a\u8be5\u89d2\u8272 Bus \u7684\u540d\u79f0\u540e\u7f00\uff1b\u628a 2P \u7684 Bus \u540e\u7f00\u586b\u6210 3P \u7684\u540e\u7f00\u5373\u8868\u793a\u4e0d\u533a\u5206 2P/3P Bus\uff0c\u4e24\u8005\u590d\u7528\u540c\u4e00\u4e2a Bus\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabNaming), QCoreApplication.translate("ProjectSettings", u"\u5de5\u7a0b\u89c4\u8303", None))
        self.cbxAutoFetchChildren.setText(QCoreApplication.translate("ProjectSettings", u"\u5de5\u5177\u6267\u884c\u524d\u81ea\u52a8\u83b7\u53d6\u5b50\u5bf9\u8c61", None))
        self.lblPageSize.setText(QCoreApplication.translate("ProjectSettings", u"\u67e5\u8be2\u5206\u9875\u5927\u5c0f", None))
#if QT_CONFIG(tooltip)
        self.lblPageSize.setToolTip(QCoreApplication.translate("ProjectSettings", u"WAAPI \u67e5\u8be2\u5b50\u5bf9\u8c61/\u540e\u4ee3/\u6279\u91cf\u67e5\u627e\u65f6\u6bcf\u6b21\u62c9\u53d6\u7684\u6570\u91cf\u3002\u8c03\u5927\u80fd\u51cf\u5c11\u8bf7\u6c42\u6b21\u6570\uff0c\u4f46\u5355\u6b21\u8bf7\u6c42\u66f4\u91cd\uff1b\u4e3b\u7a97\u53e3\u67e5\u627e\u5bf9\u8c61\u4e0e\u5404\u5de5\u5177\u5171\u7528\u8be5\u503c\u3002", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.spbPageSize.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u9ed8\u8ba4 500\uff0c\u53ef\u8c03\u8303\u56f4 50-5000\u3002\u5bf9\u8c61\u6570\u91cf\u5f88\u5927\u7684\u5de5\u7a0b\u5efa\u8bae\u4fdd\u6301 500 \u5de6\u53f3\uff0c\u907f\u514d\u5355\u6b21\u8bf7\u6c42\u8d85\u65f6\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.lblLanguagesHeader.setText(QCoreApplication.translate("ProjectSettings", u"\u672a\u63a5\u5165\u8bed\u8a00\uff08\u7528\u5206\u53f7\u5206\u9694\uff09", None))
#if QT_CONFIG(tooltip)
        self.lblLanguagesHeader.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u8fd9\u4e9b\u8bed\u8a00\u5c1a\u672a\u63a5\u5165\uff0c\u5de5\u7a0b\u68c0\u67e5\u65f6\u4e0d\u4f1a\u8981\u6c42\u5b83\u4eec\u5b58\u5728\u5bf9\u5e94\u8bed\u97f3\uff0c\u4e5f\u4e0d\u53c2\u4e0e\u672c\u5730\u5316\u68c0\u67e5\u3002\u591a\u4e2a\u8bed\u8a00\u7528\u5206\u53f7\u5206\u9694\uff0c\u4f8b\u5982 Chinese;Japanese\u3002", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.iptLanguages.setToolTip(QCoreApplication.translate("ProjectSettings", u"\u591a\u4e2a\u8bed\u8a00\u7528\u5206\u53f7\u5206\u9694\uff0c\u4f8b\u5982 Chinese;Japanese\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabTools), QCoreApplication.translate("ProjectSettings", u"\u5de5\u5177\u884c\u4e3a", None))
        self.lblAiMode.setText(QCoreApplication.translate("ProjectSettings", u"\u8fde\u63a5\u6a21\u5f0f", None))
        self.lblAiProvider.setText(QCoreApplication.translate("ProjectSettings", u"\u670d\u52a1\u63d0\u4f9b\u65b9", None))
        self.lblAiProxy.setText(QCoreApplication.translate("ProjectSettings", u"\u4ee3\u7406\u5730\u5740", None))
        self.iptAiProxy.setPlaceholderText(QCoreApplication.translate("ProjectSettings", u"http://127.0.0.1:15721", None))
        self.lblAiBaseUrl.setText(QCoreApplication.translate("ProjectSettings", u"\u81ea\u5b9a\u4e49\u5730\u5740", None))
        self.iptAiBaseUrl.setPlaceholderText(QCoreApplication.translate("ProjectSettings", u"\u5b98\u65b9\u6a21\u5f0f\u9009\u62e9\u201c\u81ea\u5b9a\u4e49\u201d\u65f6\u586b\u5199\uff0c\u5982 https://api.example.com", None))
        self.lblAiApiKey.setText(QCoreApplication.translate("ProjectSettings", u"API Key", None))
        self.lblAiModel.setText(QCoreApplication.translate("ProjectSettings", u"\u6a21\u578b", None))
        self.iptAiModel.setPlaceholderText(QCoreApplication.translate("ProjectSettings", u"\u5b98\u65b9\u6a21\u5f0f\u5efa\u8bae\u586b\u5199\uff08Claude \u5fc5\u586b\uff09\uff1b\u4ee3\u7406\u6a21\u5f0f\u53ef\u7559\u7a7a", None))
        self.cbxAiEnableScript.setText(QCoreApplication.translate("ProjectSettings", u"\u5141\u8bb8 AI \u6267\u884c\u4e34\u65f6\u811a\u672c\uff08run_wwise_script\uff1bIDE \u8c03\u8bd5\u5668\u4e0b\u53ef\u80fd\u4e0d\u7a33\u5b9a\uff0c\u9ed8\u8ba4\u5173\u95ed\uff09", None))
        self.lblAiMaxContext.setText(QCoreApplication.translate("ProjectSettings", u"\u5355\u6b21\u6700\u5927\u5bf9\u8c61\u6570", None))
        self.lblAiMaxTurns.setText(QCoreApplication.translate("ProjectSettings", u"\u6700\u5927\u5bf9\u8bdd\u8f6e\u6570", None))
        self.lblAiHint.setText(QCoreApplication.translate("ProjectSettings", u"\u8fde\u63a5\u6a21\u5f0f\uff1a\u4ee3\u7406\u6a21\u5f0f\u8d70\u672c\u5730/\u516c\u53f8\u4ee3\u7406\u5730\u5740\uff1b\u5b98\u65b9 API \u6a21\u5f0f\u6309\u201c\u670d\u52a1\u63d0\u4f9b\u65b9\u201d\u76f4\u8fde\uff08OpenAI / DeepSeek / \u901a\u4e49\u5343\u95ee / Kimi / \u667a\u8c31 GLM / Gemini / Claude / \u81ea\u5b9a\u4e49\uff09\u3002Claude \u4f7f\u7528 Anthropic \u539f\u751f\u534f\u8bae\uff0c\u5fc5\u987b\u586b\u5199\u6a21\u578b\u540d\uff1b\u5176\u4f59\u5382\u5546\u8d70 OpenAI \u517c\u5bb9\u534f\u8bae\u3002\u8bbe\u7f6e\u4fdd\u5b58\u5728 user_config.json \u7684 ai \u8282\uff0c\u4fee\u6539\u540e\u4e0b\u4e00\u6b21\u53d1\u9001\u6307\u4ee4\u751f\u6548\uff0c\u4e3b\u7a97\u53e3\u6a21\u578b\u4e0b\u62c9\u6846\u4f1a\u5728\u91cd\u542f\u540e\u540c\u6b65\u3002", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabAi), QCoreApplication.translate("ProjectSettings", u"AI \u52a9\u624b", None))
        self.lblTheme.setText(QCoreApplication.translate("ProjectSettings", u"\u754c\u9762\u4e3b\u9898", None))
        self.cbxPathDisplayCompact.setText(QCoreApplication.translate("ProjectSettings", u"\u8868\u683c\u8def\u5f84\u663e\u793a\u5173\u952e\u8bcd\u53bb\u91cd\u540e\u7684\u7b80\u5199", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabAppearance), QCoreApplication.translate("ProjectSettings", u"\u5916\u89c2", None))
        self.btnSave.setText(QCoreApplication.translate("ProjectSettings", u"\u4fdd\u5b58", None))
        self.btnCancel.setText(QCoreApplication.translate("ProjectSettings", u"\u53d6\u6d88", None))
    # retranslateUi

