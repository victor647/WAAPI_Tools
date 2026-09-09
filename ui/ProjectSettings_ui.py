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
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QHBoxLayout,
    QLabel, QLineEdit, QPlainTextEdit, QPushButton,
    QSizePolicy, QSpacerItem, QTabWidget, QVBoxLayout,
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
        self.btnSave.setText(QCoreApplication.translate("ProjectSettings", u"\u4fdd\u5b58", None))
        self.btnCancel.setText(QCoreApplication.translate("ProjectSettings", u"\u53d6\u6d88", None))
    # retranslateUi

