module load singularity-3.2.1

SubjectFile=${HOME}/msmall_Q2_2020_runs/xnat_pbs_jobs_control_CCF_HCD/failing.subjects

source ${HOME}/msmall_Q2_2020_runs/xnat_pbs_jobs_control_CCF_HCD/xnat_pbs_setup intradb

for line in $(cat $SubjectFile) ; do
	[[ "$line" =~ ^# ]] && continue
    #echo $line
	IFS=':' read -ra subject <<< "$line"
	echo "Removing running status : " ${subject[0]} ${subject[1]} ${subject[2]} ${subject[3]}

	singularity exec -B /NRG-data/NRG/intradb/archive,/NRG-data/NRG/intradb/build_ssd \
	/export/HCP/qunex-hcp/production_containers/Process/HCPpipelines_XNAT_1_0_3.sif \
	/pipeline_tools/xnat_pbs_jobs/MultiRunIcaFixProcessing/MultiRunIcaFixProcessing.XNAT_MARK_RUNNING_STATUS \
	--user="junilc" \
	--password="Aa123456" \
	--server="10.28.58.65:8080" \
	--project="${subject[0]}" \
	--subject="${subject[1]}" \
	--classifier="${subject[2]}" \
	--scan="${subject[3]}" \
	--resource="RunningStatus" \
	--done
	
done

