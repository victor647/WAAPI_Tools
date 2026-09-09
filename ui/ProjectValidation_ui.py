# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ProjectValidation.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QAbstractScrollArea, QApplication, QCheckBox,
    QDialog, QGroupBox, QHBoxLayout, QHeaderView,
    QPushButton, QSizePolicy, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget)

class Ui_ProjectValidation(object):
    def setupUi(self, ProjectValidation):
        if not ProjectValidation.objectName():
            ProjectValidation.setObjectName(u"ProjectValidation")
        ProjectValidation.resize(1010, 714)
        self.verticalLayout_5 = QVBoxLayout(ProjectValidation)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.grpProjectStandards = QGroupBox(ProjectValidation)
        self.grpProjectStandards.setObjectName(u"grpProjectStandards")
        self.grpProjectStandards.setEnabled(True)
        font = QFont()
        font.setBold(False)
        font.setItalic(False)
        self.grpProjectStandards.setFont(font)
        self.grpProjectStandards.setCheckable(True)
        self.verticalLayout_2 = QVBoxLayout(self.grpProjectStandards)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.cbxWrongCase = QCheckBox(self.grpProjectStandards)
        self.cbxWrongCase.setObjectName(u"cbxWrongCase")
        self.cbxWrongCase.setChecked(True)
        self.cbxWrongCase.setAutoRepeat(True)

        self.verticalLayout_2.addWidget(self.cbxWrongCase)

        self.cbxWrongNameLength = QCheckBox(self.grpProjectStandards)
        self.cbxWrongNameLength.setObjectName(u"cbxWrongNameLength")
        self.cbxWrongNameLength.setChecked(True)

        self.verticalLayout_2.addWidget(self.cbxWrongNameLength)

        self.cbxColorTypeMismatch = QCheckBox(self.grpProjectStandards)
        self.cbxColorTypeMismatch.setObjectName(u"cbxColorTypeMismatch")
        self.cbxColorTypeMismatch.setChecked(True)

        self.verticalLayout_2.addWidget(self.cbxColorTypeMismatch)

        self.cbxNoRefNotesOrColorTag = QCheckBox(self.grpProjectStandards)
        self.cbxNoRefNotesOrColorTag.setObjectName(u"cbxNoRefNotesOrColorTag")
        self.cbxNoRefNotesOrColorTag.setChecked(True)

        self.verticalLayout_2.addWidget(self.cbxNoRefNotesOrColorTag)


        self.horizontalLayout_2.addWidget(self.grpProjectStandards)

        self.grpDesignStructure = QGroupBox(ProjectValidation)
        self.grpDesignStructure.setObjectName(u"grpDesignStructure")
        self.grpDesignStructure.setCheckable(True)
        self.verticalLayout_4 = QVBoxLayout(self.grpDesignStructure)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.cbxNestedWorkUnit = QCheckBox(self.grpDesignStructure)
        self.cbxNestedWorkUnit.setObjectName(u"cbxNestedWorkUnit")
        self.cbxNestedWorkUnit.setChecked(True)
        self.cbxNestedWorkUnit.setAutoRepeat(True)

        self.verticalLayout_4.addWidget(self.cbxNestedWorkUnit)

        self.cbxRedundantActorMixer = QCheckBox(self.grpDesignStructure)
        self.cbxRedundantActorMixer.setObjectName(u"cbxRedundantActorMixer")
        self.cbxRedundantActorMixer.setChecked(True)

        self.verticalLayout_4.addWidget(self.cbxRedundantActorMixer)

        self.cbxSingleChildContainer = QCheckBox(self.grpDesignStructure)
        self.cbxSingleChildContainer.setObjectName(u"cbxSingleChildContainer")
        self.cbxSingleChildContainer.setChecked(True)

        self.verticalLayout_4.addWidget(self.cbxSingleChildContainer)

        self.cbxEmptyNode = QCheckBox(self.grpDesignStructure)
        self.cbxEmptyNode.setObjectName(u"cbxEmptyNode")
        self.cbxEmptyNode.setChecked(True)

        self.verticalLayout_4.addWidget(self.cbxEmptyNode)

        self.cbxDuplicatedParameter = QCheckBox(self.grpDesignStructure)
        self.cbxDuplicatedParameter.setObjectName(u"cbxDuplicatedParameter")
        self.cbxDuplicatedParameter.setChecked(True)

        self.verticalLayout_4.addWidget(self.cbxDuplicatedParameter)


        self.horizontalLayout_2.addWidget(self.grpDesignStructure)

        self.grpSoundLocalization = QGroupBox(ProjectValidation)
        self.grpSoundLocalization.setObjectName(u"grpSoundLocalization")
        self.grpSoundLocalization.setCheckable(True)
        self.verticalLayout_3 = QVBoxLayout(self.grpSoundLocalization)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.cbxSourceNameDifferent = QCheckBox(self.grpSoundLocalization)
        self.cbxSourceNameDifferent.setObjectName(u"cbxSourceNameDifferent")
        self.cbxSourceNameDifferent.setChecked(True)

        self.verticalLayout_3.addWidget(self.cbxSourceNameDifferent)

        self.cbxSourceNotImported = QCheckBox(self.grpSoundLocalization)
        self.cbxSourceNotImported.setObjectName(u"cbxSourceNotImported")
        self.cbxSourceNotImported.setChecked(True)

        self.verticalLayout_3.addWidget(self.cbxSourceNotImported)

        self.cbxSilentPlaceholder = QCheckBox(self.grpSoundLocalization)
        self.cbxSilentPlaceholder.setObjectName(u"cbxSilentPlaceholder")
        self.cbxSilentPlaceholder.setChecked(True)

        self.verticalLayout_3.addWidget(self.cbxSilentPlaceholder)

        self.cbxSoundNotInEvent = QCheckBox(self.grpSoundLocalization)
        self.cbxSoundNotInEvent.setObjectName(u"cbxSoundNotInEvent")
        self.cbxSoundNotInEvent.setChecked(True)

        self.verticalLayout_3.addWidget(self.cbxSoundNotInEvent)

        self.cbxInvalidTrimRange = QCheckBox(self.grpSoundLocalization)
        self.cbxInvalidTrimRange.setObjectName(u"cbxInvalidTrimRange")
        self.cbxInvalidTrimRange.setChecked(True)

        self.verticalLayout_3.addWidget(self.cbxInvalidTrimRange)


        self.horizontalLayout_2.addWidget(self.grpSoundLocalization)

        self.grpEventBank = QGroupBox(ProjectValidation)
        self.grpEventBank.setObjectName(u"grpEventBank")
        self.grpEventBank.setCheckable(True)
        self.verticalLayout = QVBoxLayout(self.grpEventBank)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.cbxEventDuplicatedByNetRole = QCheckBox(self.grpEventBank)
        self.cbxEventDuplicatedByNetRole.setObjectName(u"cbxEventDuplicatedByNetRole")
        self.cbxEventDuplicatedByNetRole.setChecked(True)

        self.verticalLayout.addWidget(self.cbxEventDuplicatedByNetRole)

        self.cbxWrongEventName = QCheckBox(self.grpEventBank)
        self.cbxWrongEventName.setObjectName(u"cbxWrongEventName")
        self.cbxWrongEventName.setChecked(True)

        self.verticalLayout.addWidget(self.cbxWrongEventName)

        self.cbxEmptyEvent = QCheckBox(self.grpEventBank)
        self.cbxEmptyEvent.setObjectName(u"cbxEmptyEvent")
        self.cbxEmptyEvent.setChecked(True)

        self.verticalLayout.addWidget(self.cbxEmptyEvent)

        self.cbxEventNotInBank = QCheckBox(self.grpEventBank)
        self.cbxEventNotInBank.setObjectName(u"cbxEventNotInBank")
        self.cbxEventNotInBank.setChecked(True)

        self.verticalLayout.addWidget(self.cbxEventNotInBank)

        self.cbxAbnormalBankSize = QCheckBox(self.grpEventBank)
        self.cbxAbnormalBankSize.setObjectName(u"cbxAbnormalBankSize")
        self.cbxAbnormalBankSize.setChecked(True)

        self.verticalLayout.addWidget(self.cbxAbnormalBankSize)


        self.horizontalLayout_2.addWidget(self.grpEventBank)

        self.grpMistakes = QGroupBox(ProjectValidation)
        self.grpMistakes.setObjectName(u"grpMistakes")
        self.grpMistakes.setCheckable(True)
        self.verticalLayout_6 = QVBoxLayout(self.grpMistakes)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.cbxUnassignedToBus = QCheckBox(self.grpMistakes)
        self.cbxUnassignedToBus.setObjectName(u"cbxUnassignedToBus")
        self.cbxUnassignedToBus.setChecked(True)

        self.verticalLayout_6.addWidget(self.cbxUnassignedToBus)

        self.cbxUnassignedSwitchContainer = QCheckBox(self.grpMistakes)
        self.cbxUnassignedSwitchContainer.setObjectName(u"cbxUnassignedSwitchContainer")
        self.cbxUnassignedSwitchContainer.setChecked(True)

        self.verticalLayout_6.addWidget(self.cbxUnassignedSwitchContainer)

        self.cbxSwitchTo1PByDefault = QCheckBox(self.grpMistakes)
        self.cbxSwitchTo1PByDefault.setObjectName(u"cbxSwitchTo1PByDefault")
        self.cbxSwitchTo1PByDefault.setChecked(True)

        self.verticalLayout_6.addWidget(self.cbxSwitchTo1PByDefault)

        self.cbxMissingAttenuation = QCheckBox(self.grpMistakes)
        self.cbxMissingAttenuation.setObjectName(u"cbxMissingAttenuation")
        self.cbxMissingAttenuation.setChecked(True)

        self.verticalLayout_6.addWidget(self.cbxMissingAttenuation)

        self.cbxSoundNotStreamed = QCheckBox(self.grpMistakes)
        self.cbxSoundNotStreamed.setObjectName(u"cbxSoundNotStreamed")
        self.cbxSoundNotStreamed.setChecked(True)

        self.verticalLayout_6.addWidget(self.cbxSoundNotStreamed)


        self.horizontalLayout_2.addWidget(self.grpMistakes)


        self.verticalLayout_5.addLayout(self.horizontalLayout_2)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.btnSelectAll = QPushButton(ProjectValidation)
        self.btnSelectAll.setObjectName(u"btnSelectAll")

        self.horizontalLayout.addWidget(self.btnSelectAll)

        self.btnDeselectAll = QPushButton(ProjectValidation)
        self.btnDeselectAll.setObjectName(u"btnDeselectAll")

        self.horizontalLayout.addWidget(self.btnDeselectAll)

        self.btnValidateEntireProject = QPushButton(ProjectValidation)
        self.btnValidateEntireProject.setObjectName(u"btnValidateEntireProject")

        self.horizontalLayout.addWidget(self.btnValidateEntireProject)

        self.btnValidateListEntries = QPushButton(ProjectValidation)
        self.btnValidateListEntries.setObjectName(u"btnValidateListEntries")

        self.horizontalLayout.addWidget(self.btnValidateListEntries)

        self.btnValidateProjectSelection = QPushButton(ProjectValidation)
        self.btnValidateProjectSelection.setObjectName(u"btnValidateProjectSelection")

        self.horizontalLayout.addWidget(self.btnValidateProjectSelection)

        self.btnSendResultToMainWindow = QPushButton(ProjectValidation)
        self.btnSendResultToMainWindow.setObjectName(u"btnSendResultToMainWindow")

        self.horizontalLayout.addWidget(self.btnSendResultToMainWindow)

        self.btnAutoFixSelection = QPushButton(ProjectValidation)
        self.btnAutoFixSelection.setObjectName(u"btnAutoFixSelection")

        self.horizontalLayout.addWidget(self.btnAutoFixSelection)


        self.verticalLayout_5.addLayout(self.horizontalLayout)

        self.tblValidationResults = QTableWidget(ProjectValidation)
        if (self.tblValidationResults.columnCount() < 4):
            self.tblValidationResults.setColumnCount(4)
        __qtablewidgetitem = QTableWidgetItem()
        self.tblValidationResults.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tblValidationResults.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tblValidationResults.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.tblValidationResults.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        self.tblValidationResults.setObjectName(u"tblValidationResults")
        self.tblValidationResults.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tblValidationResults.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.tblValidationResults.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tblValidationResults.setSortingEnabled(False)
        self.tblValidationResults.horizontalHeader().setProperty(u"showSortIndicator", False)

        self.verticalLayout_5.addWidget(self.tblValidationResults)


        self.retranslateUi(ProjectValidation)

        QMetaObject.connectSlotsByName(ProjectValidation)
    # setupUi

    def retranslateUi(self, ProjectValidation):
        ProjectValidation.setWindowTitle(QCoreApplication.translate("ProjectValidation", u"\u5de5\u7a0b\u89c4\u8303\u68c0\u67e5", None))
        self.grpProjectStandards.setTitle(QCoreApplication.translate("ProjectValidation", u"\u5de5\u7a0b\u89c4\u8303", None))
        self.cbxWrongCase.setText(QCoreApplication.translate("ProjectValidation", u"\u4e0d\u7b26\u5408\u5927\u5c0f\u5199\u89c4\u8303", None))
        self.cbxWrongNameLength.setText(QCoreApplication.translate("ProjectValidation", u"\u540d\u79f0\u957f\u77ed\u4e0d\u7b26\u5408\u89c4\u8303", None))
        self.cbxColorTypeMismatch.setText(QCoreApplication.translate("ProjectValidation", u"\u989c\u8272\u4e0e\u5bf9\u8c61\u7684\u7c7b\u522b\u4e0d\u4e00\u81f4", None))
        self.cbxNoRefNotesOrColorTag.setText(QCoreApplication.translate("ProjectValidation", u"\u5f15\u7528\u5907\u6ce8/\u989c\u8272\u6807\u8bb0\u7f3a\u5931\u6216\u9519\u8bef", None))
        self.grpDesignStructure.setTitle(QCoreApplication.translate("ProjectValidation", u"\u8bbe\u8ba1\u7f3a\u9677", None))
        self.cbxNestedWorkUnit.setText(QCoreApplication.translate("ProjectValidation", u"WorkUnit\u591a\u5c42\u5d4c\u5957", None))
        self.cbxRedundantActorMixer.setText(QCoreApplication.translate("ProjectValidation", u"ActorMixer\u65e0\u5b9e\u9645\u8c03\u6574", None))
        self.cbxSingleChildContainer.setText(QCoreApplication.translate("ProjectValidation", u"Container\u4ec5\u5305\u542b\u4e00\u4e2a\u5b50\u8282\u70b9", None))
        self.cbxEmptyNode.setText(QCoreApplication.translate("ProjectValidation", u"\u5bf9\u8c61\u4e0d\u5305\u542b\u6709\u6548\u5185\u5bb9", None))
        self.cbxDuplicatedParameter.setText(QCoreApplication.translate("ProjectValidation", u"RTPC\u91cd\u590d\u7ed1\u5b9a\u5185\u90e8\u5c5e\u6027", None))
        self.grpSoundLocalization.setTitle(QCoreApplication.translate("ProjectValidation", u"\u6837\u672c\u4e0e\u672c\u5730\u5316", None))
        self.cbxSourceNameDifferent.setText(QCoreApplication.translate("ProjectValidation", u"\u6e90\u6587\u4ef6\u4e0eSound\u547d\u540d\u4e0d\u4e00\u81f4", None))
        self.cbxSourceNotImported.setText(QCoreApplication.translate("ProjectValidation", u"\u672a\u5bfc\u5165\u6216\u7f3a\u5931\u8bed\u8a00", None))
        self.cbxSilentPlaceholder.setText(QCoreApplication.translate("ProjectValidation", u"\u4f7f\u7528\u9759\u97f3\u4e34\u65f6\u66ff\u4ee3\u8d44\u6e90", None))
        self.cbxSoundNotInEvent.setText(QCoreApplication.translate("ProjectValidation", u"\u97f3\u6548\u672a\u88ab\u4e8b\u4ef6\u5305\u542b", None))
        self.cbxInvalidTrimRange.setText(QCoreApplication.translate("ProjectValidation", u"\u97f3\u9891\u88c1\u526a\u8d85\u51fa\u8303\u56f4", None))
        self.grpEventBank.setTitle(QCoreApplication.translate("ProjectValidation", u"Event\u4e0eBank", None))
        self.cbxEventDuplicatedByNetRole.setText(QCoreApplication.translate("ProjectValidation", u"\u5b58\u57281P/3P\u4e24\u4e2a\u4e8b\u4ef6", None))
        self.cbxWrongEventName.setText(QCoreApplication.translate("ProjectValidation", u"Event\u4e0e\u64ad\u653e\u5bf9\u8c61\u547d\u540d\u51b2\u7a81", None))
        self.cbxEmptyEvent.setText(QCoreApplication.translate("ProjectValidation", u"Event\u7f3a\u5c11\u52a8\u4f5c\u6216\u76ee\u6807", None))
        self.cbxEventNotInBank.setText(QCoreApplication.translate("ProjectValidation", u"Event\u672a\u88ab\u4efb\u4f55Bank\u5305\u542b", None))
        self.cbxAbnormalBankSize.setText(QCoreApplication.translate("ProjectValidation", u"Bank\u8fc7\u5927\u6216\u8fc7\u5c0f", None))
        self.grpMistakes.setTitle(QCoreApplication.translate("ProjectValidation", u"\u7c97\u5fc3\u5927\u610f", None))
        self.cbxUnassignedToBus.setText(QCoreApplication.translate("ProjectValidation", u"\u672a\u6307\u5b9a\u5bf9\u5e94\u7c7b\u522b\u7684Bus", None))
        self.cbxUnassignedSwitchContainer.setText(QCoreApplication.translate("ProjectValidation", u"SwitchContainer\u672a\u5206\u914d", None))
        self.cbxSwitchTo1PByDefault.setText(QCoreApplication.translate("ProjectValidation", u"SwitchContainer\u9ed8\u8ba4\u64ad\u653e1P", None))
        self.cbxMissingAttenuation.setText(QCoreApplication.translate("ProjectValidation", u"3D\u97f3\u6548\u672a\u8bbe\u7f6e\u8870\u51cf\u66f2\u7ebf", None))
        self.cbxSoundNotStreamed.setText(QCoreApplication.translate("ProjectValidation", u"\u97f3\u4e50\u73af\u5883\u8bed\u97f3\u672aStreaming", None))
        self.btnSelectAll.setText(QCoreApplication.translate("ProjectValidation", u"\u5168\u9009", None))
        self.btnDeselectAll.setText(QCoreApplication.translate("ProjectValidation", u"\u5168\u4e0d\u9009", None))
        self.btnValidateEntireProject.setText(QCoreApplication.translate("ProjectValidation", u"\u68c0\u67e5\u6574\u4e2a\u5de5\u7a0b\uff08\u53ef\u80fd\u4f1a\u5f88\u6162\uff09", None))
        self.btnValidateListEntries.setText(QCoreApplication.translate("ProjectValidation", u"\u68c0\u67e5\u4e3b\u7a97\u53e3\u5217\u8868\u5bf9\u8c61", None))
        self.btnValidateProjectSelection.setText(QCoreApplication.translate("ProjectValidation", u"\u68c0\u67e5Wwise\u5de5\u7a0b\u9009\u4e2d\u5bf9\u8c61", None))
        self.btnSendResultToMainWindow.setText(QCoreApplication.translate("ProjectValidation", u"\u5c06\u5217\u8868\u9009\u4e2d\u9879\u53d1\u9001\u5230\u4e3b\u7a97\u53e3", None))
        self.btnAutoFixSelection.setText(QCoreApplication.translate("ProjectValidation", u"\u4e00\u952e\u4fee\u590d\u5217\u8868\u9009\u4e2d\u9879", None))
        ___qtablewidgetitem = self.tblValidationResults.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("ProjectValidation", u"\u7c7b\u522b", None))
        ___qtablewidgetitem1 = self.tblValidationResults.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("ProjectValidation", u"\u95ee\u9898", None))
        ___qtablewidgetitem2 = self.tblValidationResults.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("ProjectValidation", u"\u5bf9\u8c61\u7c7b\u578b", None))
        ___qtablewidgetitem3 = self.tblValidationResults.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("ProjectValidation", u"\u5bf9\u8c61\u8def\u5f84\uff08\u53cc\u51fb\u53ef\u5728Wwise\u5de5\u7a0b\u4e2d\u67e5\u770b\uff09", None))
    # retranslateUi

