# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'AdvancedFilter.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QGroupBox,
    QHBoxLayout, QPushButton, QRadioButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_AdvancedFilter(object):
    def setupUi(self, AdvancedFilterWindow):
        if not AdvancedFilterWindow.objectName():
            AdvancedFilterWindow.setObjectName(u"AdvancedFilterWindow")
        AdvancedFilterWindow.resize(340, 200)
        AdvancedFilterWindow.setMinimumSize(QSize(340, 0))
        self.verticalLayout = QVBoxLayout(AdvancedFilterWindow)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.cbxCaseSensitive = QCheckBox(AdvancedFilterWindow)
        self.cbxCaseSensitive.setObjectName(u"cbxCaseSensitive")

        self.verticalLayout.addWidget(self.cbxCaseSensitive)

        self.cbxOnlyIncluded = QCheckBox(AdvancedFilterWindow)
        self.cbxOnlyIncluded.setObjectName(u"cbxOnlyIncluded")

        self.verticalLayout.addWidget(self.cbxOnlyIncluded)

        self.grpEventFilter = QGroupBox(AdvancedFilterWindow)
        self.grpEventFilter.setObjectName(u"grpEventFilter")
        self.horizontalLayout = QHBoxLayout(self.grpEventFilter)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.rbnEventAll = QRadioButton(self.grpEventFilter)
        self.rbnEventAll.setObjectName(u"rbnEventAll")
        self.rbnEventAll.setChecked(True)

        self.horizontalLayout.addWidget(self.rbnEventAll)

        self.rbnEventHas = QRadioButton(self.grpEventFilter)
        self.rbnEventHas.setObjectName(u"rbnEventHas")

        self.horizontalLayout.addWidget(self.rbnEventHas)

        self.rbnEventNo = QRadioButton(self.grpEventFilter)
        self.rbnEventNo.setObjectName(u"rbnEventNo")

        self.horizontalLayout.addWidget(self.rbnEventNo)


        self.verticalLayout.addWidget(self.grpEventFilter)

        self.grpLanguageFilter = QGroupBox(AdvancedFilterWindow)
        self.grpLanguageFilter.setObjectName(u"grpLanguageFilter")
        self.horizontalLayout_2 = QHBoxLayout(self.grpLanguageFilter)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.rbnLangAll = QRadioButton(self.grpLanguageFilter)
        self.rbnLangAll.setObjectName(u"rbnLangAll")
        self.rbnLangAll.setChecked(True)

        self.horizontalLayout_2.addWidget(self.rbnLangAll)

        self.rbnLangActive = QRadioButton(self.grpLanguageFilter)
        self.rbnLangActive.setObjectName(u"rbnLangActive")

        self.horizontalLayout_2.addWidget(self.rbnLangActive)


        self.verticalLayout.addWidget(self.grpLanguageFilter)

        self.buttonRow = QHBoxLayout()
        self.buttonRow.setObjectName(u"buttonRow")
        self.buttonSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonRow.addItem(self.buttonSpacer)

        self.btnClose = QPushButton(AdvancedFilterWindow)
        self.btnClose.setObjectName(u"btnClose")

        self.buttonRow.addWidget(self.btnClose)


        self.verticalLayout.addLayout(self.buttonRow)


        self.retranslateUi(AdvancedFilterWindow)

        QMetaObject.connectSlotsByName(AdvancedFilterWindow)
    # setupUi

    def retranslateUi(self, AdvancedFilterWindow):
        AdvancedFilterWindow.setWindowTitle(QCoreApplication.translate("AdvancedFilter", u"\u9ad8\u7ea7\u7b5b\u9009", None))
        self.cbxCaseSensitive.setText(QCoreApplication.translate("AdvancedFilter", u"\u533a\u5206\u5927\u5c0f\u5199", None))
        self.cbxOnlyIncluded.setText(QCoreApplication.translate("AdvancedFilter", u"\u4ec5\u663e\u793a\u542f\u7528\u5bf9\u8c61", None))
        self.grpEventFilter.setTitle(QCoreApplication.translate("AdvancedFilter", u"Event \u5f15\u7528\u7b5b\u9009", None))
        self.rbnEventAll.setText(QCoreApplication.translate("AdvancedFilter", u"\u5168\u90e8", None))
        self.rbnEventHas.setText(QCoreApplication.translate("AdvancedFilter", u"\u88ab\u5f15\u7528", None))
        self.rbnEventNo.setText(QCoreApplication.translate("AdvancedFilter", u"\u672a\u88ab\u5f15\u7528", None))
        self.grpLanguageFilter.setTitle(QCoreApplication.translate("AdvancedFilter", u"\u8bed\u8a00\u7b5b\u9009", None))
        self.rbnLangAll.setText(QCoreApplication.translate("AdvancedFilter", u"\u5168\u90e8", None))
        self.rbnLangActive.setText(QCoreApplication.translate("AdvancedFilter", u"\u6309\u5f53\u524d\u8bed\u8a00\u7b5b\u9009", None))
        self.btnClose.setText(QCoreApplication.translate("AdvancedFilter", u"\u5173\u95ed", None))
    # retranslateUi

