# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'AudioPreview.ui'
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
    QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

from libraries.widgets.waveform_widget import WaveformWidget

class Ui_AudioPreview(object):
    def setupUi(self, AudioPreviewWindow):
        if not AudioPreviewWindow.objectName():
            AudioPreviewWindow.setObjectName(u"AudioPreviewWindow")
        AudioPreviewWindow.resize(760, 280)
        AudioPreviewWindow.setMinimumSize(QSize(760, 280))
        self.verticalLayout = QVBoxLayout(AudioPreviewWindow)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.controlsInfoRow = QHBoxLayout()
        self.controlsInfoRow.setObjectName(u"controlsInfoRow")
        self.lblInfo = QLabel(AudioPreviewWindow)
        self.lblInfo.setObjectName(u"lblInfo")

        self.controlsInfoRow.addWidget(self.lblInfo)


        self.verticalLayout.addLayout(self.controlsInfoRow)

        self.controlsFileInfoRow = QHBoxLayout()
        self.controlsFileInfoRow.setObjectName(u"controlsFileInfoRow")
        self.lblFileDetails = QLabel(AudioPreviewWindow)
        self.lblFileDetails.setObjectName(u"lblFileDetails")

        self.controlsFileInfoRow.addWidget(self.lblFileDetails)

        self.fileInfoSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.controlsFileInfoRow.addItem(self.fileInfoSpacer)


        self.verticalLayout.addLayout(self.controlsFileInfoRow)

        self.controlsRow = QHBoxLayout()
        self.controlsRow.setObjectName(u"controlsRow")
        self.infoSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.controlsRow.addItem(self.infoSpacer)

        self.lblDisplayMode = QLabel(AudioPreviewWindow)
        self.lblDisplayMode.setObjectName(u"lblDisplayMode")

        self.controlsRow.addWidget(self.lblDisplayMode)

        self.cbbDisplayMode = QComboBox(AudioPreviewWindow)
        self.cbbDisplayMode.addItem("")
        self.cbbDisplayMode.addItem("")
        self.cbbDisplayMode.setObjectName(u"cbbDisplayMode")

        self.controlsRow.addWidget(self.cbbDisplayMode)

        self.chkLoop = QCheckBox(AudioPreviewWindow)
        self.chkLoop.setObjectName(u"chkLoop")

        self.controlsRow.addWidget(self.chkLoop)

        self.btnPlay = QPushButton(AudioPreviewWindow)
        self.btnPlay.setObjectName(u"btnPlay")

        self.controlsRow.addWidget(self.btnPlay)

        self.btnStop = QPushButton(AudioPreviewWindow)
        self.btnStop.setObjectName(u"btnStop")

        self.controlsRow.addWidget(self.btnStop)

        self.btnOpenFolder = QPushButton(AudioPreviewWindow)
        self.btnOpenFolder.setObjectName(u"btnOpenFolder")

        self.controlsRow.addWidget(self.btnOpenFolder)

        self.btnZoomOut = QPushButton(AudioPreviewWindow)
        self.btnZoomOut.setObjectName(u"btnZoomOut")

        self.controlsRow.addWidget(self.btnZoomOut)

        self.btnZoomIn = QPushButton(AudioPreviewWindow)
        self.btnZoomIn.setObjectName(u"btnZoomIn")

        self.controlsRow.addWidget(self.btnZoomIn)


        self.verticalLayout.addLayout(self.controlsRow)

        self.waveform = WaveformWidget(AudioPreviewWindow)
        self.waveform.setObjectName(u"waveform")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.waveform.sizePolicy().hasHeightForWidth())
        self.waveform.setSizePolicy(sizePolicy)
        self.waveform.setMinimumSize(QSize(0, 180))

        self.verticalLayout.addWidget(self.waveform)


        self.retranslateUi(AudioPreviewWindow)

        QMetaObject.connectSlotsByName(AudioPreviewWindow)
    # setupUi

    def retranslateUi(self, AudioPreviewWindow):
        AudioPreviewWindow.setWindowTitle(QCoreApplication.translate("AudioPreview", u"\u97f3\u9891\u9884\u89c8", None))
        self.lblInfo.setText("")
        self.lblFileDetails.setText("")
        self.lblDisplayMode.setText(QCoreApplication.translate("AudioPreview", u"\u663e\u793a", None))
        self.cbbDisplayMode.setItemText(0, QCoreApplication.translate("AudioPreview", u"\u6ce2\u5f62", None))
        self.cbbDisplayMode.setItemText(1, QCoreApplication.translate("AudioPreview", u"\u9891\u8c31", None))

        self.chkLoop.setText(QCoreApplication.translate("AudioPreview", u"\u5faa\u73af", None))
        self.btnPlay.setText(QCoreApplication.translate("AudioPreview", u"\u64ad\u653e", None))
        self.btnStop.setText(QCoreApplication.translate("AudioPreview", u"\u505c\u6b62", None))
        self.btnOpenFolder.setText(QCoreApplication.translate("AudioPreview", u"\u6253\u5f00\u6587\u4ef6\u5939", None))
        self.btnZoomOut.setText(QCoreApplication.translate("AudioPreview", u"\u7f29\u5c0f", None))
        self.btnZoomIn.setText(QCoreApplication.translate("AudioPreview", u"\u653e\u5927", None))
    # retranslateUi

