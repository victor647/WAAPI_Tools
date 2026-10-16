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
    QHeaderView, QLabel, QPushButton, QSizePolicy,
    QSpacerItem, QTableView, QVBoxLayout, QWidget)

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

        self.optionSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.optionRow.addItem(self.optionSpacer)


        self.mainLayout.addLayout(self.optionRow)

        self.tblMediaSize = QTableView(MediaSize)
        self.tblMediaSize.setObjectName(u"tblMediaSize")

        self.mainLayout.addWidget(self.tblMediaSize)

        self.buttonRow = QHBoxLayout()
        self.buttonRow.setObjectName(u"buttonRow")
        self.buttonSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonRow.addItem(self.buttonSpacer)

        self.btnClose = QPushButton(MediaSize)
        self.btnClose.setObjectName(u"btnClose")

        self.buttonRow.addWidget(self.btnClose)


        self.mainLayout.addLayout(self.buttonRow)


        self.retranslateUi(MediaSize)

        QMetaObject.connectSlotsByName(MediaSize)
    # setupUi

    def retranslateUi(self, MediaSize):
        MediaSize.setWindowTitle(QCoreApplication.translate("MediaSize", u"\u5a92\u4f53\u8d44\u6e90\u5927\u5c0f", None))
        self.lblPlatform.setText(QCoreApplication.translate("MediaSize", u"\u5e73\u53f0", None))
#if QT_CONFIG(tooltip)
        self.cbbPlatform.setToolTip(QCoreApplication.translate("MediaSize", u"\u5207\u6362\u540e\u540c\u6b65\u4fee\u6539 Wwise \u91cc\u7684\u5f53\u524d\u5e73\u53f0\uff0c\u5e76\u6309\u65b0\u5e73\u53f0\u91cd\u65b0\u7edf\u8ba1\uff08wem \u5927\u5c0f\u53ea\u7edf\u8ba1\u5f53\u524d\u5e73\u53f0\uff09\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.lblLanguageFilter.setText(QCoreApplication.translate("MediaSize", u"\u8bed\u8a00\u7b5b\u9009\uff1a\u5168\u90e8\u8bed\u8a00", None))
#if QT_CONFIG(tooltip)
        self.lblLanguageFilter.setToolTip(QCoreApplication.translate("MediaSize", u"\u53e3\u5f84\u4e0e\u4e3b\u7a97\u53e3\u300c\u9ad8\u7ea7\u7b5b\u9009 \u2192 \u8bed\u8a00\u7b5b\u9009\u300d\u4e00\u81f4\uff1a\u9009\u62e9\u300c\u53ea\u663e\u793a\u5f53\u524d\u8bed\u8a00\u300d\u65f6\uff0c\u8fd9\u91cc\u4e5f\u53ea\u7edf\u8ba1\u5f53\u524d\u8bed\u8a00\u7684\u6e90\uff08SFX \u7b49\u975e\u672c\u5730\u5316\u6e90\u59cb\u7ec8\u4fdd\u7559\uff09\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.btnClose.setText(QCoreApplication.translate("MediaSize", u"\u5173\u95ed", None))
    # retranslateUi

