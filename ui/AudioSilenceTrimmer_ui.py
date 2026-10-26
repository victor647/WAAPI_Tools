# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'AudioSilenceTrimmer.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QDialog,
    QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QRadioButton, QSizePolicy, QSpacerItem, QSpinBox,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_AudioSilenceTrimmer(object):
    def setupUi(self, AudioSilenceTrimmer):
        if not AudioSilenceTrimmer.objectName():
            AudioSilenceTrimmer.setObjectName(u"AudioSilenceTrimmer")
        AudioSilenceTrimmer.resize(900, 480)
        self.verticalLayout = QVBoxLayout(AudioSilenceTrimmer)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.btnImportFiles = QPushButton(AudioSilenceTrimmer)
        self.btnImportFiles.setObjectName(u"btnImportFiles")

        self.horizontalLayout.addWidget(self.btnImportFiles)

        self.btnImportFolder = QPushButton(AudioSilenceTrimmer)
        self.btnImportFolder.setObjectName(u"btnImportFolder")

        self.horizontalLayout.addWidget(self.btnImportFolder)

        self.lblCutThreshold = QLabel(AudioSilenceTrimmer)
        self.lblCutThreshold.setObjectName(u"lblCutThreshold")

        self.horizontalLayout.addWidget(self.lblCutThreshold)

        self.spbCutThreshold = QSpinBox(AudioSilenceTrimmer)
        self.spbCutThreshold.setObjectName(u"spbCutThreshold")
        self.spbCutThreshold.setMinimum(-96)
        self.spbCutThreshold.setMaximum(0)
        self.spbCutThreshold.setValue(-60)

        self.horizontalLayout.addWidget(self.spbCutThreshold)

        self.btnAnalyzeAudio = QPushButton(AudioSilenceTrimmer)
        self.btnAnalyzeAudio.setObjectName(u"btnAnalyzeAudio")

        self.horizontalLayout.addWidget(self.btnAnalyzeAudio)

        self.btnStartTrimming = QPushButton(AudioSilenceTrimmer)
        self.btnStartTrimming.setObjectName(u"btnStartTrimming")
        font = QFont()
        font.setBold(True)
        self.btnStartTrimming.setFont(font)

        self.horizontalLayout.addWidget(self.btnStartTrimming)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.cbxTrimHead = QCheckBox(AudioSilenceTrimmer)
        self.cbxTrimHead.setObjectName(u"cbxTrimHead")
        self.cbxTrimHead.setChecked(True)

        self.horizontalLayout_2.addWidget(self.cbxTrimHead)

        self.lblTrimHeadThreshold = QLabel(AudioSilenceTrimmer)
        self.lblTrimHeadThreshold.setObjectName(u"lblTrimHeadThreshold")

        self.horizontalLayout_2.addWidget(self.lblTrimHeadThreshold)

        self.spbTrimHeadThreshold = QSpinBox(AudioSilenceTrimmer)
        self.spbTrimHeadThreshold.setObjectName(u"spbTrimHeadThreshold")
        self.spbTrimHeadThreshold.setMinimum(1)
        self.spbTrimHeadThreshold.setMaximum(10000)
        self.spbTrimHeadThreshold.setValue(20)

        self.horizontalLayout_2.addWidget(self.spbTrimHeadThreshold)

        self.lblFadeInDuration = QLabel(AudioSilenceTrimmer)
        self.lblFadeInDuration.setObjectName(u"lblFadeInDuration")

        self.horizontalLayout_2.addWidget(self.lblFadeInDuration)

        self.spbFadeInDuration = QSpinBox(AudioSilenceTrimmer)
        self.spbFadeInDuration.setObjectName(u"spbFadeInDuration")
        self.spbFadeInDuration.setMinimum(1)
        self.spbFadeInDuration.setMaximum(1000)
        self.spbFadeInDuration.setValue(10)

        self.horizontalLayout_2.addWidget(self.spbFadeInDuration)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.cbxTrimTail = QCheckBox(AudioSilenceTrimmer)
        self.cbxTrimTail.setObjectName(u"cbxTrimTail")
        self.cbxTrimTail.setChecked(True)

        self.horizontalLayout_3.addWidget(self.cbxTrimTail)

        self.lblTrimTailThreshold = QLabel(AudioSilenceTrimmer)
        self.lblTrimTailThreshold.setObjectName(u"lblTrimTailThreshold")

        self.horizontalLayout_3.addWidget(self.lblTrimTailThreshold)

        self.spbTrimTailThreshold = QSpinBox(AudioSilenceTrimmer)
        self.spbTrimTailThreshold.setObjectName(u"spbTrimTailThreshold")
        self.spbTrimTailThreshold.setMinimum(1)
        self.spbTrimTailThreshold.setMaximum(10000)
        self.spbTrimTailThreshold.setValue(100)

        self.horizontalLayout_3.addWidget(self.spbTrimTailThreshold)

        self.lblFadeOutDuration = QLabel(AudioSilenceTrimmer)
        self.lblFadeOutDuration.setObjectName(u"lblFadeOutDuration")

        self.horizontalLayout_3.addWidget(self.lblFadeOutDuration)

        self.spbFadeOutDuration = QSpinBox(AudioSilenceTrimmer)
        self.spbFadeOutDuration.setObjectName(u"spbFadeOutDuration")
        self.spbFadeOutDuration.setMinimum(1)
        self.spbFadeOutDuration.setMaximum(1000)
        self.spbFadeOutDuration.setValue(50)

        self.horizontalLayout_3.addWidget(self.spbFadeOutDuration)


        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_mode = QHBoxLayout()
        self.horizontalLayout_mode.setObjectName(u"horizontalLayout_mode")
        self.cbxSelectAll = QCheckBox(AudioSilenceTrimmer)
        self.cbxSelectAll.setObjectName(u"cbxSelectAll")

        self.horizontalLayout_mode.addWidget(self.cbxSelectAll)

        self.lblMode = QLabel(AudioSilenceTrimmer)
        self.lblMode.setObjectName(u"lblMode")

        self.horizontalLayout_mode.addWidget(self.lblMode)

        self.rbnModeTrim = QRadioButton(AudioSilenceTrimmer)
        self.rbnModeTrim.setObjectName(u"rbnModeTrim")
        self.rbnModeTrim.setChecked(True)

        self.horizontalLayout_mode.addWidget(self.rbnModeTrim)

        self.rbnModeZero = QRadioButton(AudioSilenceTrimmer)
        self.rbnModeZero.setObjectName(u"rbnModeZero")

        self.horizontalLayout_mode.addWidget(self.rbnModeZero)

        self.rbnModeWwise = QRadioButton(AudioSilenceTrimmer)
        self.rbnModeWwise.setObjectName(u"rbnModeWwise")

        self.horizontalLayout_mode.addWidget(self.rbnModeWwise)

        self.modeSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_mode.addItem(self.modeSpacer)


        self.verticalLayout.addLayout(self.horizontalLayout_mode)

        self.tblFileList = QTableWidget(AudioSilenceTrimmer)
        if (self.tblFileList.columnCount() < 6):
            self.tblFileList.setColumnCount(6)
        __qtablewidgetitem = QTableWidgetItem()
        self.tblFileList.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tblFileList.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tblFileList.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.tblFileList.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.tblFileList.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.tblFileList.setHorizontalHeaderItem(5, __qtablewidgetitem5)
        self.tblFileList.setObjectName(u"tblFileList")
        self.tblFileList.setDragEnabled(True)
        self.tblFileList.setDragDropMode(QAbstractItemView.DragDrop)

        self.verticalLayout.addWidget(self.tblFileList)


        self.retranslateUi(AudioSilenceTrimmer)

        QMetaObject.connectSlotsByName(AudioSilenceTrimmer)
    # setupUi

    def retranslateUi(self, AudioSilenceTrimmer):
        AudioSilenceTrimmer.setWindowTitle(QCoreApplication.translate("AudioSilenceTrimmer", u"\u97f3\u9891\u5934\u5c3e\u9759\u97f3\u88c1\u526a", None))
        self.btnImportFiles.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u5bfc\u5165\u6587\u4ef6", None))
        self.btnImportFolder.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u5bfc\u5165\u6587\u4ef6\u5939", None))
        self.lblCutThreshold.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u9759\u97f3\u5224\u65ad\u9608\u503c", None))
        self.spbCutThreshold.setSuffix(QCoreApplication.translate("AudioSilenceTrimmer", u"dB", None))
        self.btnAnalyzeAudio.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u5206\u6790\u97f3\u9891", None))
        self.btnStartTrimming.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u5f00\u59cb\u88c1\u526a", None))
        self.cbxTrimHead.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u88c1\u526a\u97f3\u5934", None))
        self.lblTrimHeadThreshold.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u5224\u5b9a\u9608\u503c", None))
        self.spbTrimHeadThreshold.setSuffix(QCoreApplication.translate("AudioSilenceTrimmer", u"ms", None))
        self.lblFadeInDuration.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u4fdd\u7559\u6de1\u5165", None))
        self.spbFadeInDuration.setSuffix(QCoreApplication.translate("AudioSilenceTrimmer", u"ms", None))
        self.cbxTrimTail.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u88c1\u526a\u97f3\u5c3e", None))
        self.lblTrimTailThreshold.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u5224\u5b9a\u9608\u503c", None))
        self.spbTrimTailThreshold.setSuffix(QCoreApplication.translate("AudioSilenceTrimmer", u"ms", None))
        self.lblFadeOutDuration.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u4fdd\u7559\u6de1\u51fa", None))
        self.spbFadeOutDuration.setSuffix(QCoreApplication.translate("AudioSilenceTrimmer", u"ms", None))
        self.cbxSelectAll.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u5168\u9009", None))
        self.lblMode.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u9759\u97f3\u5904\u7406\u65b9\u5f0f", None))
        self.rbnModeTrim.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u88c1\u526a\uff08\u7f29\u77ed\u6587\u4ef6\u65f6\u957f\uff09", None))
        self.rbnModeZero.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u9759\u97f3\u6539\u4e3a\u7eaf0\uff08\u65f6\u957f\u4e0d\u53d8\uff09", None))
#if QT_CONFIG(tooltip)
        self.rbnModeWwise.setToolTip(QCoreApplication.translate("AudioSilenceTrimmer", u"\u4e0d\u4fee\u6539\u6e90\u6587\u4ef6\uff0c\u6539\u4e3a\u5728 Wwise \u91cc\u8bbe\u7f6e AudioFileSource \u7684 TrimBegin / TrimEnd \u4e0e FadeIn / FadeOut\u3002TrimBegin / TrimEnd \u90fd\u662f\u4ece\u5934\u7b97\u8d77\u7684\u7edd\u5bf9\u65f6\u95f4\u4f4d\u7f6e\uff08TrimEnd = \u6587\u4ef6\u603b\u65f6\u957f \u2212 \u5c3e\u90e8\u88c1\u526a\u91cf\uff09\uff1b\u4fdd\u7559\u300c\u4fdd\u7559\u6de1\u5165/\u6de1\u51fa\u300d\u957f\u5ea6\u7684\u9759\u97f3\u4f5c\u4e3a\u6de1\u53d8\u533a\uff0c\u6548\u679c\u4e0e\u300c\u88c1\u526a\u6e90\u6587\u4ef6\u300d\u6a21\u5f0f\u4e00\u81f4\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.rbnModeWwise.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"Wwise\u5185\u90e8\u88c1\u526a\uff08\u6539Trim\u503c\uff0c\u4e0d\u52a8\u6587\u4ef6\uff09", None))
        ___qtablewidgetitem = self.tblFileList.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u97f3\u9891\u6587\u4ef6\u8def\u5f84", None))
        ___qtablewidgetitem1 = self.tblFileList.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u603b\u65f6\u957f", None))
        ___qtablewidgetitem2 = self.tblFileList.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u5934\u90e8\u9759\u97f3\u65f6\u957f", None))
        ___qtablewidgetitem3 = self.tblFileList.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u5c3e\u90e8\u9759\u97f3\u65f6\u957f", None))
        ___qtablewidgetitem4 = self.tblFileList.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u9759\u97f3\u5360\u6bd4", None))
        ___qtablewidgetitem5 = self.tblFileList.horizontalHeaderItem(5)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("AudioSilenceTrimmer", u"\u5904\u7406\u72b6\u6001", None))
    # retranslateUi

