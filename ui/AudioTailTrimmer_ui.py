# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'AudioTailTrimmer.ui'
##
## Created by: Qt User Interface Compiler version 6.9.2
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QDialog, QDoubleSpinBox,
    QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QSizePolicy, QSpinBox, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget)

class Ui_AudioTailTrimmer(object):
    def setupUi(self, AudioTailTrimmer):
        if not AudioTailTrimmer.objectName():
            AudioTailTrimmer.setObjectName(u"AudioTailTrimmer")
        AudioTailTrimmer.resize(698, 609)
        self.verticalLayout = QVBoxLayout(AudioTailTrimmer)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.btnImportFiles = QPushButton(AudioTailTrimmer)
        self.btnImportFiles.setObjectName(u"btnImportFiles")

        self.horizontalLayout.addWidget(self.btnImportFiles)

        self.btnImportFolder = QPushButton(AudioTailTrimmer)
        self.btnImportFolder.setObjectName(u"btnImportFolder")

        self.horizontalLayout.addWidget(self.btnImportFolder)

        self.btnAnalyzeTails = QPushButton(AudioTailTrimmer)
        self.btnAnalyzeTails.setObjectName(u"btnAnalyzeTails")

        self.horizontalLayout.addWidget(self.btnAnalyzeTails)

        self.btnStartTrim = QPushButton(AudioTailTrimmer)
        self.btnStartTrim.setObjectName(u"btnStartTrim")

        self.horizontalLayout.addWidget(self.btnStartTrim)

        self.lblCutThreshold = QLabel(AudioTailTrimmer)
        self.lblCutThreshold.setObjectName(u"lblCutThreshold")

        self.horizontalLayout.addWidget(self.lblCutThreshold)

        self.spbCutThreshold = QSpinBox(AudioTailTrimmer)
        self.spbCutThreshold.setObjectName(u"spbCutThreshold")
        self.spbCutThreshold.setMinimum(-96)
        self.spbCutThreshold.setMaximum(0)
        self.spbCutThreshold.setValue(-48)

        self.horizontalLayout.addWidget(self.spbCutThreshold)

        self.lblFadeDuration = QLabel(AudioTailTrimmer)
        self.lblFadeDuration.setObjectName(u"lblFadeDuration")

        self.horizontalLayout.addWidget(self.lblFadeDuration)

        self.spbFadeDuration = QDoubleSpinBox(AudioTailTrimmer)
        self.spbFadeDuration.setObjectName(u"spbFadeDuration")
        self.spbFadeDuration.setMinimum(0.010000000000000)
        self.spbFadeDuration.setMaximum(1.000000000000000)
        self.spbFadeDuration.setSingleStep(0.010000000000000)
        self.spbFadeDuration.setValue(0.100000000000000)

        self.horizontalLayout.addWidget(self.spbFadeDuration)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.tblFileList = QTableWidget(AudioTailTrimmer)
        if (self.tblFileList.columnCount() < 4):
            self.tblFileList.setColumnCount(4)
        __qtablewidgetitem = QTableWidgetItem()
        self.tblFileList.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tblFileList.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tblFileList.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.tblFileList.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        self.tblFileList.setObjectName(u"tblFileList")
        self.tblFileList.setDragEnabled(True)
        self.tblFileList.setDragDropMode(QAbstractItemView.DragDrop)

        self.verticalLayout.addWidget(self.tblFileList)


        self.retranslateUi(AudioTailTrimmer)

        QMetaObject.connectSlotsByName(AudioTailTrimmer)
    # setupUi

    def retranslateUi(self, AudioTailTrimmer):
        AudioTailTrimmer.setWindowTitle(QCoreApplication.translate("AudioTailTrimmer", u"\u5c3e\u90e8\u5197\u4f59\u9759\u97f3\u88c1\u526a\u5de5\u5177", None))
        self.btnImportFiles.setText(QCoreApplication.translate("AudioTailTrimmer", u"\u5bfc\u5165\u6587\u4ef6", None))
        self.btnImportFolder.setText(QCoreApplication.translate("AudioTailTrimmer", u"\u5bfc\u5165\u6587\u4ef6\u5939", None))
        self.btnAnalyzeTails.setText(QCoreApplication.translate("AudioTailTrimmer", u"\u5206\u6790\u5197\u4f59\u65f6\u957f", None))
        self.btnStartTrim.setText(QCoreApplication.translate("AudioTailTrimmer", u"\u5f00\u59cb\u88c1\u526a\u97f3\u5c3e", None))
        self.lblCutThreshold.setText(QCoreApplication.translate("AudioTailTrimmer", u"\u9759\u97f3\u5224\u65ad\u9608\u503c", None))
        self.spbCutThreshold.setSuffix(QCoreApplication.translate("AudioTailTrimmer", u"dB", None))
        self.lblFadeDuration.setText(QCoreApplication.translate("AudioTailTrimmer", u"\u6de1\u51fa\u65f6\u957f", None))
        self.spbFadeDuration.setSuffix(QCoreApplication.translate("AudioTailTrimmer", u"s", None))
        ___qtablewidgetitem = self.tblFileList.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("AudioTailTrimmer", u"\u97f3\u9891\u6587\u4ef6\u540d", None));
        ___qtablewidgetitem1 = self.tblFileList.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("AudioTailTrimmer", u"\u603b\u65f6\u957f", None));
        ___qtablewidgetitem2 = self.tblFileList.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("AudioTailTrimmer", u"\u5c3e\u90e8\u9759\u97f3\u65f6\u957f", None));
        ___qtablewidgetitem3 = self.tblFileList.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("AudioTailTrimmer", u"\u5904\u7406\u72b6\u6001", None));
    # retranslateUi

