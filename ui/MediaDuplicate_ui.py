# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'MediaDuplicate.ui'
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
    QDialog, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QTableView,
    QVBoxLayout, QWidget)

class Ui_MediaDuplicate(object):
    def setupUi(self, MediaDuplicate):
        if not MediaDuplicate.objectName():
            MediaDuplicate.setObjectName(u"MediaDuplicate")
        MediaDuplicate.resize(1120, 480)
        MediaDuplicate.setMinimumSize(QSize(640, 360))
        self.mainLayout = QVBoxLayout(MediaDuplicate)
        self.mainLayout.setObjectName(u"mainLayout")
        self.fileRow = QHBoxLayout()
        self.fileRow.setObjectName(u"fileRow")
        self.lblSoundBanksInfo = QLabel(MediaDuplicate)
        self.lblSoundBanksInfo.setObjectName(u"lblSoundBanksInfo")

        self.fileRow.addWidget(self.lblSoundBanksInfo)

        self.iptSoundBanksInfoPath = QLineEdit(MediaDuplicate)
        self.iptSoundBanksInfoPath.setObjectName(u"iptSoundBanksInfoPath")
        self.iptSoundBanksInfoPath.setReadOnly(True)

        self.fileRow.addWidget(self.iptSoundBanksInfoPath)

        self.lblPlatform = QLabel(MediaDuplicate)
        self.lblPlatform.setObjectName(u"lblPlatform")

        self.fileRow.addWidget(self.lblPlatform)

        self.btnChooseFile = QPushButton(MediaDuplicate)
        self.btnChooseFile.setObjectName(u"btnChooseFile")

        self.fileRow.addWidget(self.btnChooseFile)

        self.btnReparse = QPushButton(MediaDuplicate)
        self.btnReparse.setObjectName(u"btnReparse")

        self.fileRow.addWidget(self.btnReparse)

        self.btnAutoFix = QPushButton(MediaDuplicate)
        self.btnAutoFix.setObjectName(u"btnAutoFix")
        self.btnAutoFix.setEnabled(False)

        self.fileRow.addWidget(self.btnAutoFix)


        self.mainLayout.addLayout(self.fileRow)

        self.filterRow = QHBoxLayout()
        self.filterRow.setObjectName(u"filterRow")
        self.lblFilter = QLabel(MediaDuplicate)
        self.lblFilter.setObjectName(u"lblFilter")

        self.filterRow.addWidget(self.lblFilter)

        self.iptFilter = QLineEdit(MediaDuplicate)
        self.iptFilter.setObjectName(u"iptFilter")

        self.filterRow.addWidget(self.iptFilter)

        self.cbbCauseFilter = QComboBox(MediaDuplicate)
        self.cbbCauseFilter.setObjectName(u"cbbCauseFilter")
        self.cbbCauseFilter.setMinimumSize(QSize(150, 0))

        self.filterRow.addWidget(self.cbbCauseFilter)

        self.cbxSingleCauseOnly = QCheckBox(MediaDuplicate)
        self.cbxSingleCauseOnly.setObjectName(u"cbxSingleCauseOnly")

        self.filterRow.addWidget(self.cbxSingleCauseOnly)

        self.lblFilterResult = QLabel(MediaDuplicate)
        self.lblFilterResult.setObjectName(u"lblFilterResult")

        self.filterRow.addWidget(self.lblFilterResult)

        self.btnExportJson = QPushButton(MediaDuplicate)
        self.btnExportJson.setObjectName(u"btnExportJson")
        self.btnExportJson.setEnabled(False)

        self.filterRow.addWidget(self.btnExportJson)


        self.mainLayout.addLayout(self.filterRow)

        self.lblStatus = QLabel(MediaDuplicate)
        self.lblStatus.setObjectName(u"lblStatus")
        self.lblStatus.setWordWrap(True)

        self.mainLayout.addWidget(self.lblStatus)

        self.tblDuplicates = QTableView(MediaDuplicate)
        self.tblDuplicates.setObjectName(u"tblDuplicates")
        self.tblDuplicates.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tblDuplicates.setAlternatingRowColors(True)
        self.tblDuplicates.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tblDuplicates.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tblDuplicates.setSortingEnabled(True)
        self.tblDuplicates.setWordWrap(False)
        self.tblDuplicates.horizontalHeader().setStretchLastSection(False)
        self.tblDuplicates.verticalHeader().setVisible(False)

        self.mainLayout.addWidget(self.tblDuplicates)


        self.retranslateUi(MediaDuplicate)

        QMetaObject.connectSlotsByName(MediaDuplicate)
    # setupUi

    def retranslateUi(self, MediaDuplicate):
        MediaDuplicate.setWindowTitle(QCoreApplication.translate("MediaDuplicate", u"\u5a92\u4f53\u67e5\u91cd", None))
        self.lblSoundBanksInfo.setText(QCoreApplication.translate("MediaDuplicate", u"SoundBanksInfo.xml", None))
        self.iptSoundBanksInfoPath.setPlaceholderText(QCoreApplication.translate("MediaDuplicate", u"\u542f\u52a8\u65f6\u9009\u62e9 SoundBanksInfo.xml", None))
        self.lblPlatform.setText(QCoreApplication.translate("MediaDuplicate", u"\u5e73\u53f0\uff1a-", None))
        self.btnChooseFile.setText(QCoreApplication.translate("MediaDuplicate", u"\u9009\u62e9\u6587\u4ef6\u2026", None))
#if QT_CONFIG(tooltip)
        self.btnReparse.setToolTip(QCoreApplication.translate("MediaDuplicate", u"\u91cd\u65b0\u89e3\u6790\u5f53\u524d SoundBanksInfo.xml\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.btnReparse.setText(QCoreApplication.translate("MediaDuplicate", u"\u91cd\u65b0\u89e3\u6790", None))
#if QT_CONFIG(tooltip)
        self.btnAutoFix.setToolTip(QCoreApplication.translate("MediaDuplicate", u"\u81ea\u52a8\u5904\u7406\u5f53\u524d\u7b5b\u9009\u7ed3\u679c\u4e2d\u7684\u5faa\u73af\u8bbe\u7f6e\u3001\u6de1\u5165\u6de1\u51fa\u548c\u6548\u679c\u5668\u6e32\u67d3\u95ee\u9898\uff1b\u6240\u6709\u4fee\u6539\u5408\u5e76\u4e3a\u4e00\u4e2a\u64a4\u9500\u7ec4\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.btnAutoFix.setText(QCoreApplication.translate("MediaDuplicate", u"\u81ea\u52a8\u5904\u7406", None))
        self.lblFilter.setText(QCoreApplication.translate("MediaDuplicate", u"\u7b5b\u9009", None))
        self.iptFilter.setPlaceholderText(QCoreApplication.translate("MediaDuplicate", u"\u539f\u59cb\u97f3\u9891\u8def\u5f84\uff1b\u7528 ; \u5206\u9694\u591a\u4e2a\u5173\u952e\u8bcd\uff0c\u524d\u7f00 - \u8868\u793a\u6392\u9664", None))
#if QT_CONFIG(tooltip)
        self.cbbCauseFilter.setToolTip(QCoreApplication.translate("MediaDuplicate", u"\u53ea\u663e\u793a\u5305\u542b\u6240\u9009\u91cd\u590d\u539f\u56e0\u7684\u9879\u76ee\uff1b\u591a\u539f\u56e0\u9879\u76ee\u547d\u4e2d\u4efb\u610f\u4e00\u4e2a\u5373\u663e\u793a\uff08\u52fe\u9009\u201c\u4ec5\u663e\u793a\u5355\u4e00\u539f\u56e0\u201d\u540e\u9690\u85cf\uff09\u3002", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.cbxSingleCauseOnly.setToolTip(QCoreApplication.translate("MediaDuplicate", u"\u53ea\u663e\u793a\u4ec5\u547d\u4e2d\u4e00\u4e2a\u91cd\u590d\u539f\u56e0\u7684\u9879\u76ee\uff0c\u9690\u85cf\u591a\u539f\u56e0\u9879\u76ee\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxSingleCauseOnly.setText(QCoreApplication.translate("MediaDuplicate", u"\u4ec5\u663e\u793a\u5355\u4e00\u539f\u56e0", None))
        self.lblFilterResult.setText(QCoreApplication.translate("MediaDuplicate", u"\u663e\u793a 0 / 0 \u884c", None))
#if QT_CONFIG(tooltip)
        self.btnExportJson.setToolTip(QCoreApplication.translate("MediaDuplicate", u"\u5bfc\u51fa\u5f53\u524d\u7b5b\u9009\u7ed3\u679c\uff08\u4fdd\u6301\u5f53\u524d\u6392\u5e8f\uff09\uff0c\u5305\u542b\u6bcf\u4e2a wem\u3001Event \u4e0e AudioFileSource \u7684\u8be6\u7ec6\u4fe1\u606f\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.btnExportJson.setText(QCoreApplication.translate("MediaDuplicate", u"\u5bfc\u51fa JSON", None))
        self.lblStatus.setText(QCoreApplication.translate("MediaDuplicate", u"\u8bf7\u9009\u62e9 SoundBanksInfo.xml \u6587\u4ef6\u3002", None))
    # retranslateUi

