"""Broker QA tổng hợp: không import CSDL, feature, auth hay dữ liệu thật."""
import secrets

class DemoBroker:
    def __init__(self,state='idle'):
        self.state=state;self.token=None;self.reads=0
    def _enabled(self):pass
    def issue(self,session,*,ttl=300):
        if session!='synthetic-owner':raise PermissionError()
        self.token=secrets.token_urlsafe(32);return self.token
    def snapshot(self,token):
        if token!=self.token:raise PermissionError()
        self.reads+=1
        rows=[{'id':'QA-RED','state':'waiting_admin','due_status':'red'},
              {'id':'QA-YELLOW','state':'waiting_admin','due_status':'yellow'},
              {'id':'QA-MERGE','state':'waiting_merge','due_status':'green'}] if self.state=='tickets' else []
        return {'schema_version':1,'enabled':True,'available':True,
                'ticket_counts':{'waiting_admin':2 if rows else 0,'waiting_merge':1 if rows else 0},'ticket_summaries':rows,
                'qa_reads':self.reads}
