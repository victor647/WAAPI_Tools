# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'MediaSize.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QPushButton,
    QRadioButton, QSizePolicy, QSpacerItem, QTableView,
    QVBoxLayout, QWidget)

class Ui_MediaSize(object):
    def setupUi(self, MediaSize):
        if not MediaSize.objectName():
            MediaSize.setObjectName(u"MediaSize")
        MediaSize.resize(1100, 430)
        self.mainLayout = QVBoxLayout(MediaSize)
        self.mainLayout.setObjectName(u"mainLayout")
        self.optionRow = QHBoxLayout()
        self.optionRow.setObjectName(u"optionRow")
        self.lblPlatform = QLabel(MediaSize)
        self.lblPlatform.setObjectName(u"lblPlatform")

        self.optionRow.addWidget(self.lblPlatform)

        self.cbbPlatform = QComboBox(MediaSize)
        self.cbbPlatform.setObjectName(u"cbbPlatform")
        self.cbbPlatform.setMinimumSize(QSize(150, 0))

        self.optionRow.addWidget(self.cbbPlatform)

        self.lblLanguageFilter = QLabel(MediaSize)
        self.lblLanguageFilter.setObjectName(u"lblLanguageFilter")

        self.optionRow.addWidget(self.lblLanguageFilter)

        self.rbnLangAll = QRadioButton(MediaSize)
        self.rbnLangAll.setObjectName(u"rbnLangAll")
        self.rbnLangAll.setChecked(True)

        self.optionRow.addWidget(self.rbnLangAll)

        self.rbnLangActive = QRadioButton(MediaSize)
        self.rbnLangActive.setObjectName(u"rbnLangActive")

        self.optionRow.addWidget(self.rbnLangActive)

        self.optionSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.optionRow.addItem(self.optionSpacer)


        self.mainLayout.addLayout(self.optionRow)

        self.xmlRow = QHBoxLayout()
        self.xmlRow.setObjectName(u"xmlRow")
        self.lblSoundBanksInfo = QLabel(MediaSize)
        self.lblSoundBanksInfo.setObjectName(u"lblSoundBanksInfo")

        self.xmlRow.addWidget(self.lblSoundBanksInfo)

        self.iptSoundBanksInfoPath = QLineEdit(MediaSize)
        self.iptSoundBanksInfoPath.setObjectName(u"iptSoundBanksInfoPath")

        self.xmlRow.addWidget(self.iptSoundBanksInfoPath)

        self.btnChooseSoundBanksInfo = QPushButton(MediaSize)
        self.btnChooseSoundBanksInfo.setObjectName(u"btnChooseSoundBanksInfo")

        self.xmlRow.addWidget(self.btnChooseSoundBanksInfo)

        self.btnClearSoundBanksInfo = QPushButton(MediaSize)
        self.btnClearSoundBanksInfo.setObjectName(u"btnClearSoundBanksInfo")

        self.xmlRow.addWidget(self.btnClearSoundBanksInfo)

        self.lblSoundBanksInfoStatus = QLabel(MediaSize)
        self.lblSoundBanksInfoStatus.setObjectName(u"lblSoundBanksInfoStatus")

        self.xmlRow.addWidget(self.lblSoundBanksInfoStatus)


        self.mainLayout.addLayout(self.xmlRow)

        self.tblMediaSize = QTableView(MediaSize)
        self.tblMediaSize.setObjectName(u"tblMediaSize")

        self.mainLayout.addWidget(self.tblMediaSize)

        self.buttonRow = QHBoxLayout()
        self.buttonRow.setObjectName(u"buttonRow")
        self.buttonSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonRow.addItem(self.buttonSpacer)

        self.btnAnalyze = QPushButton(MediaSize)
        self.btnAnalyze.setObjectName(u"btnAnalyze")

        self.buttonRow.addWidget(self.btnAnalyze)


        self.mainLayout.addLayout(self.buttonRow)


        self.retranslateUi(MediaSize)

        QMetaObject.connectSlotsByName(MediaSize)
    # setupUi

    def retranslateUi(self, MediaSize):
        MediaSize.setWindowTitle(QCoreApplication.translate("MediaSize", u"\u5a92\u4f53\u8d44\u6e90\u5927\u5c0f", None))
        self.lblPlatform.setText(QCoreApplication.translate("MediaSize", u"\u5e73\u53f0", None))
#if QT_CONFIG(tooltip)
        self.cbbPlatform.setToolTip(QCoreApplication.translate("MediaSize", u"\u5207\u6362\u540e\u540c\u6b65\u4fee\u6539 Wwise \u91cc\u7684\u5f53\u524d\u5e73\u53f0\uff1b\u70b9\u51fb\u300c\u5206\u6790\u300d\u540e\u6309\u65b0\u5e73\u53f0\u7edf\u8ba1\uff08wem \u5927\u5c0f\u53ea\u7edf\u8ba1\u5f53\u524d\u5e73\u53f0\uff09\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.lblLanguageFilter.setText(QCoreApplication.translate("MediaSize", u"\u8bed\u8a00\u7b5b\u9009", None))
#if QT_CONFIG(tooltip)
        self.rbnLangAll.setToolTip(QCoreApplication.translate("MediaSize", u"\u7edf\u8ba1\u5168\u90e8\u8bed\u8a00\u3002\u4e0e\u300c\u9ad8\u7ea7\u7b5b\u9009 \u2192 \u8bed\u8a00\u7b5b\u9009\u300d\u5171\u7528\u540c\u4e00\u8bbe\u7f6e\uff1b\u70b9\u51fb\u300c\u5206\u6790\u300d\u540e\u751f\u6548\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.rbnLangAll.setText(QCoreApplication.translate("MediaSize", u"\u5168\u90e8\u8bed\u8a00", None))
#if QT_CONFIG(tooltip)
        self.rbnLangActive.setToolTip(QCoreApplication.translate("MediaSize", u"\u53ea\u7edf\u8ba1\u5f53\u524d\u8bed\u8a00\u7684\u6e90\uff08SFX \u7b49\u975e\u672c\u5730\u5316\u6e90\u59cb\u7ec8\u4fdd\u7559\uff09\u3002\u4e0e\u300c\u9ad8\u7ea7\u7b5b\u9009 \u2192 \u8bed\u8a00\u7b5b\u9009\u300d\u5171\u7528\u540c\u4e00\u8bbe\u7f6e\uff1b\u70b9\u51fb\u300c\u5206\u6790\u300d\u540e\u751f\u6548\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.rbnLangActive.setText(QCoreApplication.translate("MediaSize", u"\u5f53\u524d\u8bed\u8a00", None))
        self.lblSoundBanksInfo.setText(QCoreApplication.translate("MediaSize", u"SoundBanksInfo.xml", None))
        self.iptSoundBanksInfoPath.setPlaceholderText(QCoreApplication.translate("MediaSize", u"\u53ef\u9009\uff1a\u672c\u5730\u672a\u751f\u6210 Bank \u65f6\uff0c\u7528 XML \u4e2d\u7684\u6253\u5305 wem \u8def\u5f84\u8865\u5168\u5927\u5c0f", None))
        self.btnChooseSoundBanksInfo.setText(QCoreApplication.translate("MediaSize", u"\u9009\u62e9...", None))
        self.btnClearSoundBanksInfo.setText(QCoreApplication.translate("MediaSize", u"\u6e05\u9664", None))
        self.lblSoundBanksInfoStatus.setText(QCoreApplication.translate("MediaSize", u"\u4ec5\u4f7f\u7528\u672c\u5730 wem", None))
#if QT_CONFIG(tooltip)
        self.btnAnalyze.setToolTip(QCoreApplication.translate("MediaSize", u"\u6309\u5f53\u524d\u5e73\u53f0\u3001\u8bed\u8a00\u7b5b\u9009\u548c SoundBanksInfo.xml \u8bbe\u7f6e\u7edf\u8ba1\u5a92\u4f53\u8d44\u6e90\u5927\u5c0f\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.btnAnalyze.setText(QCoreApplication.translate("MediaSize", u"\u5206\u6790", None))
    # retranslateUi

