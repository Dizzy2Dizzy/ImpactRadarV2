import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export const metadata = {
  title: "Data Processing Agreement | Impact Radar",
  description: "Data Processing Agreement for Enterprise customers",
};

export default function DPAPage() {
  return (
    <div className="min-h-screen bg-[--background]">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="mx-auto max-w-4xl px-6 lg:px-8">
          <div className="text-center mb-12">
            <h1 className="text-4xl font-semibold tracking-tight text-[--text]">
              Data Processing Agreement
            </h1>
            <p className="mt-4 text-[--muted]">
              Last updated: November 18, 2025
            </p>
          </div>

          <div className="prose prose-invert max-w-none">
            <div className="space-y-8 text-[--muted]">
              <section>
                <div className="p-6 bg-blue-500/10 border border-blue-500/20 rounded-lg mb-8">
                  <p className="text-[--text]">
                    This Data Processing Agreement ("DPA") forms part of the Terms of Service between Impact Radar ("Processor") and the customer ("Controller") and applies to Enterprise plan customers who process personal data through our Service in accordance with GDPR and other applicable data protection laws.
                  </p>
                </div>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">1. Definitions</h2>
                <p>
                  For the purposes of this DPA:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li><strong>"Controller"</strong> means the Enterprise customer who determines the purposes and means of processing personal data</li>
                  <li><strong>"Processor"</strong> means Impact Radar, which processes personal data on behalf of the Controller</li>
                  <li><strong>"Personal Data"</strong> means any information relating to an identified or identifiable natural person</li>
                  <li><strong>"Data Subject"</strong> means the individual to whom Personal Data relates</li>
                  <li><strong>"Processing"</strong> means any operation performed on Personal Data, including collection, storage, use, or disclosure</li>
                  <li><strong>"Sub-processor"</strong> means any third-party processor engaged by the Processor</li>
                  <li><strong>"Data Protection Laws"</strong> means GDPR, CCPA, and other applicable data protection regulations</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">2. Scope and Roles</h2>
                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">2.1 Application</h3>
                <p>
                  This DPA applies to Personal Data processed by Impact Radar on behalf of the Controller through the Service, including but not limited to:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>End user account information</li>
                  <li>Watchlist and portfolio data</li>
                  <li>Alert configuration data</li>
                  <li>API usage logs</li>
                  <li>Team member information</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">2.2 Roles and Responsibilities</h3>
                <p>
                  The parties acknowledge and agree that:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>The Controller determines the purposes and means of processing Personal Data</li>
                  <li>Impact Radar acts as a Processor and processes Personal Data only on documented instructions from the Controller</li>
                  <li>The Controller is responsible for ensuring it has legal grounds for processing under applicable Data Protection Laws</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">3. Processor Obligations</h2>
                
                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">3.1 Processing Instructions</h3>
                <p>
                  Impact Radar shall:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Process Personal Data only on documented instructions from the Controller, including regarding transfers of Personal Data to third countries</li>
                  <li>Immediately inform the Controller if it believes an instruction violates Data Protection Laws</li>
                  <li>Not process Personal Data for any purpose other than providing the Service</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">3.2 Confidentiality</h3>
                <p>
                  Impact Radar shall ensure that persons authorized to process Personal Data:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Are subject to confidentiality obligations</li>
                  <li>Receive appropriate training on data protection</li>
                  <li>Access Personal Data only as necessary for their duties</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">3.3 Security Measures</h3>
                <p>
                  Impact Radar implements appropriate technical and organizational measures including:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li><strong>Encryption:</strong> TLS/SSL encryption for data in transit, encryption at rest for sensitive data</li>
                  <li><strong>Access Controls:</strong> Role-based access control, multi-factor authentication</li>
                  <li><strong>Network Security:</strong> Firewalls, intrusion detection, regular security audits</li>
                  <li><strong>Data Integrity:</strong> Regular backups, disaster recovery procedures</li>
                  <li><strong>Incident Response:</strong> Security incident monitoring and response procedures</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">4. Sub-processors</h2>
                
                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">4.1 Authorization</h3>
                <p>
                  The Controller authorizes Impact Radar to engage Sub-processors to assist in providing the Service, subject to the terms of this DPA.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">4.2 Current Sub-processors</h3>
                <p>Impact Radar currently engages the following Sub-processors:</p>
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full divide-y divide-white/10">
                    <thead>
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-semibold text-[--text]">Sub-processor</th>
                        <th className="px-4 py-3 text-left text-sm font-semibold text-[--text]">Purpose</th>
                        <th className="px-4 py-3 text-left text-sm font-semibold text-[--text]">Location</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/10">
                      <tr>
                        <td className="px-4 py-3 text-sm">Replit</td>
                        <td className="px-4 py-3 text-sm">Cloud hosting and infrastructure</td>
                        <td className="px-4 py-3 text-sm">United States</td>
                      </tr>
                      <tr>
                        <td className="px-4 py-3 text-sm">Stripe</td>
                        <td className="px-4 py-3 text-sm">Payment processing</td>
                        <td className="px-4 py-3 text-sm">United States</td>
                      </tr>
                      <tr>
                        <td className="px-4 py-3 text-sm">Resend</td>
                        <td className="px-4 py-3 text-sm">Email delivery</td>
                        <td className="px-4 py-3 text-sm">United States</td>
                      </tr>
                      <tr>
                        <td className="px-4 py-3 text-sm">Sentry</td>
                        <td className="px-4 py-3 text-sm">Error monitoring</td>
                        <td className="px-4 py-3 text-sm">United States</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">4.3 Sub-processor Changes</h3>
                <p>
                  Impact Radar will:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Provide at least 30 days' notice before adding or replacing Sub-processors</li>
                  <li>Maintain an updated list of Sub-processors at impactradar.co/sub-processors</li>
                  <li>Allow the Controller to object to new Sub-processors on reasonable data protection grounds</li>
                  <li>If the Controller objects, work with the Controller to find a solution or allow the Controller to terminate the agreement</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">4.4 Sub-processor Requirements</h3>
                <p>
                  Impact Radar ensures that Sub-processors:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Are bound by data protection obligations equivalent to those in this DPA</li>
                  <li>Implement appropriate security measures</li>
                  <li>Only process Personal Data as instructed</li>
                  <li>Remain fully liable to the Controller for Sub-processor obligations</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">5. Data Subject Rights</h2>
                <p>
                  To the extent legally permitted, Impact Radar will:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Promptly notify the Controller if it receives a request from a Data Subject</li>
                  <li>Not respond to Data Subject requests directly (unless required by law)</li>
                  <li>Provide reasonable assistance to the Controller in responding to Data Subject requests</li>
                  <li>Make available mechanisms for Data Subjects to exercise their rights (access, rectification, erasure, etc.)</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">6. Data Breach Notification</h2>
                
                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">6.1 Notification Obligation</h3>
                <p>
                  Impact Radar shall notify the Controller without undue delay (and in any event within 72 hours) upon becoming aware of a Personal Data breach affecting the Controller's data.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">6.2 Breach Information</h3>
                <p>
                  The notification shall include:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Description of the breach, including categories and approximate number of Data Subjects affected</li>
                  <li>Name and contact details of the data protection officer or other contact point</li>
                  <li>Description of likely consequences of the breach</li>
                  <li>Description of measures taken or proposed to address the breach</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">6.3 Assistance</h3>
                <p>
                  Impact Radar shall provide reasonable assistance to the Controller in meeting its obligations regarding breach notification to supervisory authorities and Data Subjects.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">7. Data Protection Impact Assessment</h2>
                <p>
                  Impact Radar shall provide reasonable assistance to the Controller in conducting Data Protection Impact Assessments and prior consultations with supervisory authorities, including:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Providing information about processing activities</li>
                  <li>Describing security measures in place</li>
                  <li>Documenting data flows and Sub-processors</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">8. International Transfers</h2>
                
                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">8.1 Transfer Mechanisms</h3>
                <p>
                  For transfers of Personal Data from the EEA to third countries, Impact Radar relies on:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Standard Contractual Clauses approved by the European Commission</li>
                  <li>Adequacy decisions where applicable</li>
                  <li>Other appropriate safeguards as required by Data Protection Laws</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">8.2 Data Storage Locations</h3>
                <p>
                  Personal Data is primarily stored in data centers located in the United States. Upon request, Impact Radar can provide information about specific data center locations.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">9. Audit Rights</h2>
                <p>
                  Impact Radar shall make available to the Controller all information necessary to demonstrate compliance with this DPA and allow for audits and inspections:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>The Controller may conduct audits once per year upon reasonable notice (at least 30 days)</li>
                  <li>Audits shall be conducted during business hours and shall not unreasonably interfere with operations</li>
                  <li>The Controller shall bear all costs of audits unless material non-compliance is found</li>
                  <li>Impact Radar may provide standard audit reports (SOC 2, ISO 27001) in lieu of on-site audits</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">10. Data Return and Deletion</h2>
                
                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">10.1 Upon Termination</h3>
                <p>
                  Upon termination of the Service, Impact Radar shall, at the Controller's choice:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Return all Personal Data to the Controller in a structured, commonly used format</li>
                  <li>Delete all Personal Data, unless required to retain by law</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">10.2 Deletion Timeline</h3>
                <p>
                  Personal Data deletion shall occur within 90 days of termination, except for:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Backups retained for disaster recovery (deleted within 180 days)</li>
                  <li>Data required to be retained by law</li>
                  <li>Anonymized data used for analytics</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">10.3 Certification</h3>
                <p>
                  Upon request, Impact Radar shall provide written certification of data deletion.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">11. Liability and Indemnification</h2>
                <p>
                  Each party's liability arising out of or related to this DPA shall be subject to the limitation of liability provisions in the Terms of Service. The parties agree that any regulatory fines levied as a result of Personal Data processing shall be allocated based on responsibility for the violation.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">12. Duration and Termination</h2>
                <p>
                  This DPA shall remain in effect for the duration of the Service agreement and shall automatically terminate upon termination of the Service agreement. Sections relating to data return, deletion, and confidentiality shall survive termination.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">13. Amendments</h2>
                <p>
                  Impact Radar may amend this DPA from time to time to reflect changes in Data Protection Laws or processing activities. Material amendments will be communicated to the Controller with at least 30 days' notice.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">14. Governing Law</h2>
                <p>
                  This DPA shall be governed by the same law as the Terms of Service. In the event of conflict between this DPA and the Terms of Service, this DPA shall prevail with respect to Personal Data processing.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">15. Contact for Data Protection Matters</h2>
                <p>
                  For questions or concerns regarding data processing under this DPA, please contact:
                </p>
                <div className="mt-4 p-4 bg-[--panel] rounded-lg border border-white/10">
                  <p className="font-semibold text-[--text]">Impact Radar - Data Protection Officer</p>
                  <p>Email: dpo@impactradar.co</p>
                  <p>Privacy Email: privacy@impactradar.co</p>
                  <p>Enterprise Support: enterprise@impactradar.co</p>
                </div>
              </section>

              <section className="mt-12 p-6 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                <h2 className="text-xl font-semibold text-[--text] mb-4">Enterprise Customers</h2>
                <p>
                  This DPA is automatically incorporated into Enterprise subscription agreements. Enterprise customers who require a customized DPA or have specific compliance requirements should contact enterprise@impactradar.co to discuss custom terms.
                </p>
              </section>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
