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
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QSizePolicy, QSpacerItem, QSpinBox,
    QTabWidget, QVBoxLayout, QWidget)

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
        self.lblCategoryHeader = QLabel(self.tabNaming)
        self.lblCategoryHeader.setObjectName(u"lblCategoryHeader")

        self.tabNamingLayout.addWidget(self.lblCategoryHeader)

        self.categoryMap = MapEdit(self.tabNaming)
        self.categoryMap.setObjectName(u"categoryMap")
        self.categoryMap.setMinimumSize(QSize(0, 200))

        self.tabNamingLayout.addWidget(self.categoryMap)

        self.lblContainerHeader = QLabel(self.tabNaming)
        self.lblContainerHeader.setObjectName(u"lblContainerHeader")

        self.tabNamingLayout.addWidget(self.lblContainerHeader)

        self.containerSuffix = MapEdit(self.tabNaming)
        self.containerSuffix.setObjectName(u"containerSuffix")
        self.containerSuffix.setMinimumSize(QSize(0, 150))

        self.tabNamingLayout.addWidget(self.containerSuffix)

        self.cbxFullNameInSound = QCheckBox(self.tabNaming)
        self.cbxFullNameInSound.setObjectName(u"cbxFullNameInSound")

        self.tabNamingLayout.addWidget(self.cbxFullNameInSound)

        self.cbxPlayPrefixInEvent = QCheckBox(self.tabNaming)
        self.cbxPlayPrefixInEvent.setObjectName(u"cbxPlayPrefixInEvent")

        self.tabNamingLayout.addWidget(self.cbxPlayPrefixInEvent)

        self.tabWidget.addTab(self.tabNaming, "")
        self.tabHabits = QWidget()
        self.tabHabits.setObjectName(u"tabHabits")
        self.tabHabitsLayout = QVBoxLayout(self.tabHabits)
        self.tabHabitsLayout.setObjectName(u"tabHabitsLayout")
        self.suffixRow = QHBoxLayout()
        self.suffixRow.setObjectName(u"suffixRow")
        self.lblSuffixLabel = QLabel(self.tabHabits)
        self.lblSuffixLabel.setObjectName(u"lblSuffixLabel")

        self.suffixRow.addWidget(self.lblSuffixLabel)

        self.suffixSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.suffixRow.addItem(self.suffixSpacer)

        self.lblRole1P = QLabel(self.tabHabits)
        self.lblRole1P.setObjectName(u"lblRole1P")

        self.suffixRow.addWidget(self.lblRole1P)

        self.iptNetRole1P = QLineEdit(self.tabHabits)
        self.iptNetRole1P.setObjectName(u"iptNetRole1P")

        self.suffixRow.addWidget(self.iptNetRole1P)

        self.lblRole2P = QLabel(self.tabHabits)
        self.lblRole2P.setObjectName(u"lblRole2P")

        self.suffixRow.addWidget(self.lblRole2P)

        self.iptNetRole2P = QLineEdit(self.tabHabits)
        self.iptNetRole2P.setObjectName(u"iptNetRole2P")

        self.suffixRow.addWidget(self.iptNetRole2P)

        self.lblRole3P = QLabel(self.tabHabits)
        self.lblRole3P.setObjectName(u"lblRole3P")

        self.suffixRow.addWidget(self.lblRole3P)

        self.iptNetRole3P = QLineEdit(self.tabHabits)
        self.iptNetRole3P.setObjectName(u"iptNetRole3P")

        self.suffixRow.addWidget(self.iptNetRole3P)


        self.tabHabitsLayout.addLayout(self.suffixRow)

        self.lblGroupHeader = QLabel(self.tabHabits)
        self.lblGroupHeader.setObjectName(u"lblGroupHeader")

        self.tabHabitsLayout.addWidget(self.lblGroupHeader)

        self.iptNetRoleGroup = QLineEdit(self.tabHabits)
        self.iptNetRoleGroup.setObjectName(u"iptNetRoleGroup")

        self.tabHabitsLayout.addWidget(self.iptNetRoleGroup)

        self.lblValuesHeader = QLabel(self.tabHabits)
        self.lblValuesHeader.setObjectName(u"lblValuesHeader")

        self.tabHabitsLayout.addWidget(self.lblValuesHeader)

        self.netRoleValues = MapEdit(self.tabHabits)
        self.netRoleValues.setObjectName(u"netRoleValues")
        self.netRoleValues.setMinimumSize(QSize(0, 150))

        self.tabHabitsLayout.addWidget(self.netRoleValues)

        self.lblLanguagesHeader = QLabel(self.tabHabits)
        self.lblLanguagesHeader.setObjectName(u"lblLanguagesHeader")

        self.tabHabitsLayout.addWidget(self.lblLanguagesHeader)

        self.pteLanguages = QPlainTextEdit(self.tabHabits)
        self.pteLanguages.setObjectName(u"pteLanguages")
        self.pteLanguages.setMinimumSize(QSize(0, 120))

        self.tabHabitsLayout.addWidget(self.pteLanguages)

        self.tabWidget.addTab(self.tabHabits, "")
        self.tabTools = QWidget()
        self.tabTools.setObjectName(u"tabTools")
        self.tabToolsLayout = QVBoxLayout(self.tabTools)
        self.tabToolsLayout.setObjectName(u"tabToolsLayout")
        self.cbxAutoFetchChildren = QCheckBox(self.tabTools)
        self.cbxAutoFetchChildren.setObjectName(u"cbxAutoFetchChildren")

        self.tabToolsLayout.addWidget(self.cbxAutoFetchChildren)

        self.toolsSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.tabToolsLayout.addItem(self.toolsSpacer)

        self.tabWidget.addTab(self.tabTools, "")
        self.tabAi = QWidget()
        self.tabAi.setObjectName(u"tabAi")
        self.tabAiLayout = QVBoxLayout(self.tabAi)
        self.tabAiLayout.setObjectName(u"tabAiLayout")
        self.aiForm = QFormLayout()
        self.aiForm.setObjectName(u"aiForm")
        self.lblAiProxy = QLabel(self.tabAi)
        self.lblAiProxy.setObjectName(u"lblAiProxy")

        self.aiForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblAiProxy)

        self.iptAiProxy = QLineEdit(self.tabAi)
        self.iptAiProxy.setObjectName(u"iptAiProxy")

        self.aiForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.iptAiProxy)

        self.lblAiApiKey = QLabel(self.tabAi)
        self.lblAiApiKey.setObjectName(u"lblAiApiKey")

        self.aiForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lblAiApiKey)

        self.iptAiApiKey = QLineEdit(self.tabAi)
        self.iptAiApiKey.setObjectName(u"iptAiApiKey")
        self.iptAiApiKey.setEchoMode(QLineEdit.Password)

        self.aiForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.iptAiApiKey)

        self.lblAiModel = QLabel(self.tabAi)
        self.lblAiModel.setObjectName(u"lblAiModel")

        self.aiForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lblAiModel)

        self.iptAiModel = QLineEdit(self.tabAi)
        self.iptAiModel.setObjectName(u"iptAiModel")

        self.aiForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.iptAiModel)

        self.lblAiMaxContext = QLabel(self.tabAi)
        self.lblAiMaxContext.setObjectName(u"lblAiMaxContext")

        self.aiForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lblAiMaxContext)

        self.spnAiMaxContext = QSpinBox(self.tabAi)
        self.spnAiMaxContext.setObjectName(u"spnAiMaxContext")
        self.spnAiMaxContext.setMinimum(1)
        self.spnAiMaxContext.setMaximum(10000)
        self.spnAiMaxContext.setValue(300)

        self.aiForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.spnAiMaxContext)

        self.lblAiMaxTurns = QLabel(self.tabAi)
        self.lblAiMaxTurns.setObjectName(u"lblAiMaxTurns")

        self.aiForm.setWidget(4, QFormLayout.ItemRole.LabelRole, self.lblAiMaxTurns)

        self.spnAiMaxTurns = QSpinBox(self.tabAi)
        self.spnAiMaxTurns.setObjectName(u"spnAiMaxTurns")
        self.spnAiMaxTurns.setMinimum(1)
        self.spnAiMaxTurns.setMaximum(200)
        self.spnAiMaxTurns.setValue(20)

        self.aiForm.setWidget(4, QFormLayout.ItemRole.FieldRole, self.spnAiMaxTurns)


        self.tabAiLayout.addLayout(self.aiForm)

        self.lblAiHint = QLabel(self.tabAi)
        self.lblAiHint.setObjectName(u"lblAiHint")
        self.lblAiHint.setWordWrap(True)

        self.tabAiLayout.addWidget(self.lblAiHint)

        self.aiSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.tabAiLayout.addItem(self.aiSpacer)

        self.tabWidget.addTab(self.tabAi, "")

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
        self.lblCategoryHeader.setText(QCoreApplication.translate("ProjectSettings", u"\u5206\u7c7b\u547d\u540d\u4e0e\u989c\u8272\uff08\u5206\u7c7b\u540d \u2192 \u7f29\u5199 / Wwise \u989c\u8272\u503c\uff09", None))
        self.lblContainerHeader.setText(QCoreApplication.translate("ProjectSettings", u"\u5bb9\u5668\u7c7b\u578b\u540e\u7f00\uff08\u5bb9\u5668\u7c7b\u578b \u2192 \u540d\u79f0\u540e\u7f00\uff09", None))
        self.cbxFullNameInSound.setText(QCoreApplication.translate("ProjectSettings", u"Sound \u8282\u70b9\u4f7f\u7528\u5b8c\u6574\u540d\u79f0", None))
        self.cbxPlayPrefixInEvent.setText(QCoreApplication.translate("ProjectSettings", u"Event \u4ee5 Play_ \u5f00\u5934", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabNaming), QCoreApplication.translate("ProjectSettings", u"\u547d\u540d\u4e0e\u989c\u8272\u89c4\u8303", None))
        self.lblSuffixLabel.setText(QCoreApplication.translate("ProjectSettings", u"1P/2P/3P \u540e\u7f00", None))
        self.lblRole1P.setText(QCoreApplication.translate("ProjectSettings", u"1P", None))
        self.lblRole2P.setText(QCoreApplication.translate("ProjectSettings", u"2P", None))
        self.lblRole3P.setText(QCoreApplication.translate("ProjectSettings", u"3P", None))
        self.lblGroupHeader.setText(QCoreApplication.translate("ProjectSettings", u"NetRole SwitchGroup \u540d\u79f0", None))
        self.lblValuesHeader.setText(QCoreApplication.translate("ProjectSettings", u"1P/2P/3P \u5bf9\u5e94\u7684 Switch \u503c", None))
        self.lblLanguagesHeader.setText(QCoreApplication.translate("ProjectSettings", u"\u5df2\u63a5\u5165\u8bed\u8a00\uff08\u6bcf\u884c\u4e00\u4e2a\uff09", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabHabits), QCoreApplication.translate("ProjectSettings", u"\u5de5\u7a0b\u4e60\u60ef", None))
        self.cbxAutoFetchChildren.setText(QCoreApplication.translate("ProjectSettings", u"\u5de5\u5177\u6267\u884c\u524d\u81ea\u52a8\u83b7\u53d6\u5b50\u5bf9\u8c61", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabTools), QCoreApplication.translate("ProjectSettings", u"\u5de5\u5177\u884c\u4e3a", None))
        self.lblAiProxy.setText(QCoreApplication.translate("ProjectSettings", u"\u4ee3\u7406\u5730\u5740", None))
        self.iptAiProxy.setPlaceholderText(QCoreApplication.translate("ProjectSettings", u"http://127.0.0.1:15721", None))
        self.lblAiApiKey.setText(QCoreApplication.translate("ProjectSettings", u"API Key", None))
        self.lblAiModel.setText(QCoreApplication.translate("ProjectSettings", u"\u6a21\u578b", None))
        self.iptAiModel.setPlaceholderText(QCoreApplication.translate("ProjectSettings", u"\u7559\u7a7a\u8868\u793a\u4e0d\u6307\u5b9a\u6a21\u578b", None))
        self.lblAiMaxContext.setText(QCoreApplication.translate("ProjectSettings", u"\u5355\u6b21\u6700\u5927\u5bf9\u8c61\u6570", None))
        self.lblAiMaxTurns.setText(QCoreApplication.translate("ProjectSettings", u"\u6700\u5927\u5bf9\u8bdd\u8f6e\u6570", None))
        self.lblAiHint.setText(QCoreApplication.translate("ProjectSettings", u"AI \u52a9\u624b\u8bbe\u7f6e\u4fdd\u5b58\u5728 user_config.json \u7684 ai \u8282\uff1a\u4ee3\u7406\u4e3a OpenAI \u517c\u5bb9\u5730\u5740\uff1b\u6a21\u578b\u53ef\u7559\u7a7a\uff1b\u4fee\u6539\u540e\u4e0b\u4e00\u6b21\u53d1\u9001\u6307\u4ee4\u751f\u6548\uff0c\u4e3b\u7a97\u53e3\u7684\u6a21\u578b\u4e0b\u62c9\u6846\u4f1a\u5728\u91cd\u542f\u540e\u540c\u6b65\u3002", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabAi), QCoreApplication.translate("ProjectSettings", u"AI \u52a9\u624b", None))
        self.btnSave.setText(QCoreApplication.translate("ProjectSettings", u"\u4fdd\u5b58", None))
        self.btnCancel.setText(QCoreApplication.translate("ProjectSettings", u"\u53d6\u6d88", None))
    # retranslateUi

