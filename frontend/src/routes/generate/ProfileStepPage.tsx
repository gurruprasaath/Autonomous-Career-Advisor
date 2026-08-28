import { useNavigate } from 'react-router-dom'
import ProfileForm, { type ProfileFormValues } from '../../components/ProfileForm'
import WizardSteps from './WizardSteps'
import { loadWizardState, saveWizardState } from './wizardStorage'

export default function ProfileStepPage() {
  const navigate = useNavigate()
  const { profileInput } = loadWizardState()

  const handleSubmit = (values: ProfileFormValues) => {
    saveWizardState({ profileInput: values })
    navigate('/generate/role')
  }

  return (
    <>
      <WizardSteps current={0} />
      <ProfileForm initialValues={profileInput} onSubmit={handleSubmit} />
    </>
  )
}
